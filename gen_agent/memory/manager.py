"""
MemoryManager — main orchestrator for the Gen_Agent memory system.

Responsibilities:
  - Accept store/retrieve/touch/delete requests.
  - Delegate persistence to a backend (SQLiteMemoryBackend by default).
  - Score and rank retrieved memories via MemoryDecayEngine.

This class implements MemoryProtocol implicitly (structural subtyping via Protocol).
"""
from __future__ import annotations

import time
import uuid
from typing import Any, List, Optional

from gen_agent.interfaces.memory_protocol import MemoryQuery, MemoryRecord
from gen_agent.memory.decay import MemoryDecayEngine, get_decay_engine
from gen_agent.memory.models import Memory
from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend


class MemoryManager:
    """
    Facade over storage + decay engine.

    Thread-safe as long as the underlying backend is thread-safe
    (SQLiteMemoryBackend is).
    """

    def __init__(
        self,
        backend: Optional[SQLiteMemoryBackend] = None,
        decay_engine: Optional[MemoryDecayEngine] = None,
    ) -> None:
        self._backend = backend or SQLiteMemoryBackend()
        self._decay = decay_engine or get_decay_engine()

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
        self._backend.store(record)
        return memory.memory_id

    def retrieve(self, query: MemoryQuery) -> List[MemoryRecord]:
        """
        Retrieve and rank memories by composite score (recency + importance + relevance).
        Returns top-k after scoring.
        """
        candidates = self._backend.retrieve(query)

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
