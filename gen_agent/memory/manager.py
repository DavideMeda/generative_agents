"""
MemoryManager — main orchestrator for the Gen_Agent memory system.

Optional advanced layers (all injected, None = disabled):
  graphrag   — GraphRAGRetriever for semantic + graph-expanded retrieval
  mars       — MaRSEngine for privacy filtering and retention policies
  compressor — MemoryCompressor for periodic DB compression

This class implements MemoryProtocol implicitly (structural subtyping via Protocol).
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from gen_agent.interfaces.memory_protocol import MemoryQuery, MemoryRecord
from gen_agent.memory.decay import MemoryDecayEngine, get_decay_engine
from gen_agent.memory.models import Memory
from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Facade over storage + decay engine + optional advanced layers.

    Thread-safe as long as the underlying backend is thread-safe
    (SQLiteMemoryBackend uses a threading.Lock).
    """

    def __init__(
        self,
        backend: Optional[SQLiteMemoryBackend] = None,
        decay_engine: Optional[MemoryDecayEngine] = None,
        graphrag: Optional[Any] = None,   # GraphRAGRetriever | None
        mars: Optional[Any] = None,        # MaRSEngine | None
        compressor: Optional[Any] = None,  # MemoryCompressor | None
    ) -> None:
        self._backend = backend or SQLiteMemoryBackend()
        self._decay = decay_engine or get_decay_engine()
        self._graphrag = graphrag
        self._mars = mars
        self._compressor = compressor

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
        record = MemoryRecord(
            memory_id=memory.memory_id,
            agent_id=memory.agent_id,
            content=memory.content,
            memory_type=memory.memory_type,
            importance=memory.importance,
            created_at=memory.created_at,
            last_accessed=memory.last_accessed,
            extra=memory.extra,
        )

        # GraphRAG: also indexes the memory in the knowledge graph
        if self._graphrag is not None:
            self._graphrag.store(agent_id, content, memory_type, importance, **kwargs)
        else:
            self._backend.store(record)

        return memory.memory_id

    def retrieve(self, query: MemoryQuery) -> List[MemoryRecord]:
        """
        Retrieve and rank memories by composite score.
        Uses GraphRAG retriever if enabled, otherwise plain SQLite.
        """
        if self._graphrag is not None:
            candidates = self._graphrag.retrieve(query)
        else:
            candidates = self._backend.retrieve(query)

        # MaRS: filter out private memories from cross-agent access
        # (In single-agent queries this is a no-op; multi-agent diffusion uses can_share())
        if self._mars is not None:
            candidates = [
                r for r in candidates
                if self._mars.classification(r.content) != "private"
                or r.agent_id == query.agent_id
            ]

        # Re-score and re-rank using the decay engine
        memory_objects = [
            Memory(
                memory_id=r.memory_id,
                agent_id=r.agent_id,
                content=r.content,
                memory_type=r.memory_type,
                importance=r.importance,
                created_at=r.created_at,
                last_accessed=r.last_accessed,
                extra=r.extra,
            )
            for r in candidates
        ]
        scored = sorted(
            zip(memory_objects, candidates),
            key=lambda pair: self._decay.score(pair[0], query.query_text),
            reverse=True,
        )
        return [record for _, record in scored[: query.top_k]]

    def touch(self, memory_id: str) -> None:
        self._backend.touch(memory_id)

    def delete(self, memory_id: str) -> None:
        self._backend.delete(memory_id)

    def count(self, agent_id: Optional[str] = None) -> int:
        return self._backend.count(agent_id)

    def maybe_compress(self, tick: int, agent_ids: List[str]) -> None:
        """Call each tick from engine; compression runs only every N ticks."""
        if self._compressor is None:
            return
        if not self._compressor.should_run(tick):
            return
        for agent_id in agent_ids:
            self._compressor.compress_agent(agent_id)
