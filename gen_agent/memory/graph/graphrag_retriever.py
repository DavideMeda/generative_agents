"""
GraphRAGRetriever — implements MemoryProtocol using the KnowledgeGraph.

retrieve() combines:
  1. Keyword overlap (BM25-lite)
  2. Graph traversal to expand related memories

Falls back to the underlying SQLiteMemoryBackend for persistence.
Registered as ENABLE_GRAPHRAG=true in MemoryManager.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

from gen_agent.interfaces.memory_protocol import MemoryQuery, MemoryRecord
from gen_agent.memory.graph.knowledge_graph import KnowledgeGraph
from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend

logger = logging.getLogger(__name__)

_STOP_WORDS = {"the", "a", "an", "is", "it", "to", "of", "in", "and", "that", "i", "we", "my", "you"}


def _keywords(text: str) -> set[str]:
    return {w.lower() for w in re.split(r"\W+", text) if len(w) > 2 and w.lower() not in _STOP_WORDS}


class GraphRAGRetriever:
    """
    MemoryProtocol wrapper that enhances retrieval via the KnowledgeGraph.

    write path: store() → SQLiteBackend + KnowledgeGraph.add_memory()
    read path: retrieve() = keyword match + graph-expanded memory IDs
    """

    def __init__(
        self,
        backend: SQLiteMemoryBackend | None = None,
        graph: KnowledgeGraph | None = None,
    ) -> None:
        self._backend = backend or SQLiteMemoryBackend()
        self._graph = graph or KnowledgeGraph()

    def store(
        self,
        agent_id: str,
        content: str,
        memory_type: str,
        importance: float,
        **kwargs: Any,
    ) -> str:
        import time
        import uuid

        from gen_agent.interfaces.memory_protocol import MemoryRecord

        mem_id = str(kwargs.get("memory_id") or uuid.uuid4())
        record = MemoryRecord(
            memory_id=mem_id,
            agent_id=agent_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            created_at=float(kwargs.get("created_at", time.time())),
            last_accessed=float(kwargs.get("last_accessed", time.time())),
            extra={k: v for k, v in kwargs.items() if k not in ("memory_id", "created_at", "last_accessed")},
        )
        self._backend.store(record)
        self._graph.add_memory(mem_id, content)
        return mem_id

    def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]:
        query_kw = _keywords(query.query_text)

        # 1. Get all memories for agent
        all_query = MemoryQuery(
            agent_id=query.agent_id, query_text="", top_k=500
        )
        candidates = self._backend.retrieve(all_query)

        # 2. Graph traversal: expand via related entity memory IDs
        related_ids: set[str] = set()
        for entity in query_kw:
            related_ids |= self._graph.related_memory_ids(entity, depth=2)

        # 3. Score: keyword overlap + graph bonus
        scored = []
        for rec in candidates:
            rec_kw = _keywords(rec.content)
            kw_score = len(rec_kw & query_kw) / max(len(rec_kw | query_kw), 1)
            graph_bonus = 0.2 if rec.memory_id in related_ids else 0.0
            scored.append((kw_score + graph_bonus, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [rec for _, rec in scored[: query.top_k]]

    def touch(self, memory_id: str) -> None:
        self._backend.touch(memory_id)

    def delete(self, memory_id: str) -> None:
        self._backend.delete(memory_id)


def make_graphrag_if_enabled(backend: Any = None) -> GraphRAGRetriever | None:
    if os.getenv("ENABLE_GRAPHRAG", "false").lower() in ("1", "true", "yes"):
        return GraphRAGRetriever(backend=backend)
    return None
