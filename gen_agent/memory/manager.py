"""
MemoryManager — main orchestrator for the Gen_Agent memory system.

Optional advanced layers (all injected, None = disabled):
  graphrag   — GraphRAGRetriever for semantic + graph-expanded retrieval
  mars       — MaRSEngine for privacy filtering and retention policies
  compressor — MemoryCompressor for periodic DB compression
  llm        — LLM callable for LLM-generated reflections

This class implements MemoryProtocol implicitly (structural subtyping via Protocol).
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog

from gen_agent.interfaces.memory_protocol import MemoryQuery, MemoryRecord
from gen_agent.memory.decay import MemoryDecayEngine
from gen_agent.memory.models import Memory
from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend

logger = structlog.get_logger(__name__)


class MemoryManager:
    """
    Facade over storage + decay engine + optional advanced layers.

    Thread-safe as long as the underlying backend is thread-safe
    (SQLiteMemoryBackend uses a threading.Lock).
    """

    # Reflection triggers (from legacy UniversalMemoryManager)
    REFLECTION_MODULO = 5           # trigger after every N new memories
    REFLECTION_SALIENCE_THRESHOLD = 7.0
    REFLECTION_SALIENCE_MIN_RECENT = 3
    MAX_IMMEDIATE_MEMORIES = 30     # consolidate oldest when exceeded

    def __init__(
        self,
        backend: SQLiteMemoryBackend | None = None,
        decay_engine: MemoryDecayEngine | None = None,
        graphrag: Any | None = None,   # GraphRAGRetriever | None
        mars: Any | None = None,        # MaRSEngine | None
        compressor: Any | None = None,  # MemoryCompressor | None
        data_dir: str = "data",
        llm: Callable[[str], str] | None = None,
        reflection_trigger: int = 5,
        consolidation_interval: int = 50,
    ) -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._agent_backends: dict[str, SQLiteMemoryBackend] = {}
        self._backend = backend or SQLiteMemoryBackend(str(self._data_dir / "central_memory.db"))
        self._decay = decay_engine or MemoryDecayEngine()
        self._graphrag = graphrag
        self._mars = mars
        self._compressor = compressor
        self._vector_store: Any | None = None
        self._llm = llm
        self._reflection_trigger = reflection_trigger
        self._consolidation_interval = consolidation_interval
        # Per-agent counters for reflection triggers
        self._agent_memory_count: dict[str, int] = {}
        self._agent_last_salience_reflect: dict[str, int] = {}
        self._agent_reflection_count: dict[str, int] = {}
        self._stats_reflections: int = 0

    def ensure_agent(self, agent_id: str) -> None:
        """Create per-agent SQLite DB at data/agents/{id}/memory.db."""
        if agent_id in self._agent_backends:
            return
        agent_dir = self._data_dir / "agents" / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        self._agent_backends[agent_id] = SQLiteMemoryBackend(str(agent_dir / "memory.db"))

    def _backend_for(self, agent_id: str) -> SQLiteMemoryBackend:
        self.ensure_agent(agent_id)
        return self._agent_backends[agent_id]

    # ------------------------------------------------------------------
    # MemoryProtocol implementation
    # ------------------------------------------------------------------

    def store(
        self,
        agent_id: str,
        content: str,
        memory_type: str,
        importance: float,
        **kwargs: Any,
    ) -> str:
        """Create and persist a new memory. Returns the new memory_id."""
        # MaRS: apply privacy policy (importance floor)
        if self._mars is not None:
            importance = self._mars.apply_to_importance(content, importance)

        memory = Memory(
            agent_id=agent_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            extra=kwargs,
        )
        record = memory.to_record()

        # GraphRAG: also indexes the memory in the knowledge graph
        backend = self._backend_for(agent_id)
        if self._graphrag is not None:
            self._graphrag._backend = backend  # ponytail: per-agent DB swap
            self._graphrag.store(agent_id, content, memory_type, importance, memory_id=memory.memory_id, **kwargs)
        else:
            backend.store(record)

        # Track count and maybe trigger reflection
        count = self._agent_memory_count.get(agent_id, 0) + 1
        self._agent_memory_count[agent_id] = count
        self._maybe_trigger_reflection(agent_id, count, importance)

        return memory.memory_id

    # ------------------------------------------------------------------
    # Reflection and consolidation
    # ------------------------------------------------------------------

    def _maybe_trigger_reflection(self, agent_id: str, count: int, importance: float) -> None:
        """Trigger reflection on modulo-N or high-salience events."""
        # Modulo trigger
        if count % self._reflection_trigger == 0:
            self._run_reflection(agent_id)
            return
        # Salience trigger: importance > threshold and at least N memories since last
        if importance >= self.REFLECTION_SALIENCE_THRESHOLD:
            last = self._agent_last_salience_reflect.get(agent_id, 0)
            if count - last >= self.REFLECTION_SALIENCE_MIN_RECENT:
                self._agent_last_salience_reflect[agent_id] = count
                self._run_reflection(agent_id)

    def _run_reflection(self, agent_id: str) -> None:
        from gen_agent.memory.reflection import generate_reflection
        try:
            backend = self._backend_for(agent_id)
            # Retrieve top 5 memories by importance
            records = backend.retrieve(
                MemoryQuery(agent_id=agent_id, query_text="", top_k=5,
                            memory_types=["observation", "social", "plan"])
            )
            if not records:
                return

            # Use a placeholder name (agent_id) if no name available
            reflection_text = generate_reflection(
                agent_id=agent_id,
                agent_name=agent_id,
                memories=records,
                llm=self._llm,
            )
            if not reflection_text:
                return

            # Store the reflection as a "reflection" memory
            self.store(
                agent_id=agent_id,
                content=reflection_text,
                memory_type="reflection",
                importance=6.0,
            )
            self._agent_reflection_count[agent_id] = self._agent_reflection_count.get(agent_id, 0) + 1
            self._stats_reflections += 1
            logger.debug("Reflection generated for %s (total: %d)", agent_id, self._stats_reflections)
        except Exception as exc:
            logger.warning("Reflection failed for %s: %s", agent_id, exc)

    def run_consolidation_batch(self, agent_ids: list[str], tick: int) -> None:
        """Consolidate oldest low-importance memories to keep DB lean."""
        if tick % self._consolidation_interval != 0:
            return
        for agent_id in agent_ids:
            try:
                backend = self._backend_for(agent_id)
                records = backend.retrieve(
                    MemoryQuery(agent_id=agent_id, query_text="", top_k=200,
                                memory_types=["observation", "social"])
                )
                if len(records) <= self.MAX_IMMEDIATE_MEMORIES:
                    continue
                # Score: low importance + not recently accessed = candidate for removal
                scored = sorted(records, key=lambda r: r.importance)
                to_drop = scored[:len(records) - self.MAX_IMMEDIATE_MEMORIES]
                for r in to_drop:
                    backend.delete(r.memory_id)
                logger.debug("Consolidated %d memories for %s", len(to_drop), agent_id)
            except Exception as exc:
                logger.warning("Consolidation failed for %s: %s", agent_id, exc)

    def reflection_stats(self) -> dict[str, Any]:
        return {
            "total_reflections": self._stats_reflections,
            "per_agent": dict(self._agent_reflection_count),
        }

    def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]:
        """
        Retrieve and rank memories by composite score.
        Uses GraphRAG retriever if enabled, otherwise plain SQLite.
        """
        if self._graphrag is not None:
            self._graphrag._backend = self._backend_for(query.agent_id)
            candidates = self._graphrag.retrieve(query)
        else:
            candidates = self._backend_for(query.agent_id).retrieve(query)

        # MaRS: filter out private memories from cross-agent access
        # (In single-agent queries this is a no-op; multi-agent diffusion uses can_share())
        if self._mars is not None:
            candidates = [
                r for r in candidates
                if self._mars.classification(r.content) != "private"
                or r.agent_id == query.agent_id
            ]

        # Re-score and re-rank using the decay engine (MemoryRecord has all needed fields)
        scored = sorted(
            candidates,
            key=lambda r: self._decay.score(r, query.query_text),
            reverse=True,
        )
        return scored[: query.top_k]

    def touch(self, memory_id: str, agent_id: str | None = None) -> None:
        if agent_id:
            self._backend_for(agent_id).touch(memory_id)
        else:
            self._backend.touch(memory_id)

    def delete(self, memory_id: str, agent_id: str | None = None) -> None:
        if agent_id:
            self._backend_for(agent_id).delete(memory_id)
        else:
            self._backend.delete(memory_id)

    def count(self, agent_id: str | None = None) -> int:
        if agent_id:
            return self._backend_for(agent_id).count(agent_id)
        total = self._backend.count(agent_id)
        for bid in self._agent_backends.values():
            total += bid.count(agent_id)
        return total

    def run_decay_batch(self, agent_ids: list[str], tick: int) -> None:
        """Apply importance decay across all agent DBs every N ticks."""
        if tick % 10 != 0:
            return
        for agent_id in agent_ids:
            backend = self._backend_for(agent_id)
            records = backend.retrieve(MemoryQuery(agent_id=agent_id, query_text="", top_k=200))
            for record in records:
                new_imp = max(0.1, record.importance * (0.95 + 0.05 * self._decay.recency_score(record.last_accessed)))
                if new_imp < record.importance - 0.01:
                    record.importance = new_imp
                    backend.store(record)

    def maybe_compress(self, tick: int, agent_ids: list[str]) -> None:
        """Call each tick from engine; compression runs only every N ticks."""
        if self._compressor is None:
            return
        if not self._compressor.should_run(tick):
            return
        for agent_id in agent_ids:
            self._compressor.compress_agent(agent_id)
