"""Optional FAISS vector memory — requires faiss-cpu (extra research)."""
from __future__ import annotations

import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class FaissVectorStore:
    """ponytail: naive in-memory fallback when faiss not installed."""

    def __init__(self) -> None:
        self._vectors: List[List[float]] = []
        self._ids: List[str] = []
        self._faiss = None
        try:
            import faiss  # type: ignore
            self._faiss = faiss
        except ImportError:
            logger.info("faiss-cpu not installed — vector store uses keyword fallback")

    def add(self, memory_id: str, embedding: List[float]) -> None:
        self._ids.append(memory_id)
        self._vectors.append(embedding)

    def search(self, embedding: List[float], top_k: int = 5) -> List[str]:
        if not self._ids:
            return []
        # ponytail: O(n) cosine without faiss
        def dot(a: List[float], b: List[float]) -> float:
            return sum(x * y for x, y in zip(a, b))
        scores = [(dot(embedding, v), mid) for v, mid in zip(self._vectors, self._ids)]
        scores.sort(reverse=True)
        return [mid for _, mid in scores[:top_k]]


def attach_vector_store(memory_manager: Any) -> None:
    """Attach optional vector index to MemoryManager."""
    store = FaissVectorStore()
    memory_manager._vector_store = store  # ponytail: duck-typed extension
    logger.info("Vector memory store attached (faiss=%s)", store._faiss is not None)
