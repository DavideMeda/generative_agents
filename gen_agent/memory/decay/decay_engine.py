"""
Ebbinghaus-curve memory decay engine.

Computes a composite retrieval score for a memory based on:
  - recency   (exponential decay since last access)
  - importance (normalized 0–1 from stored value)
  - relevance  (cosine-like keyword overlap, stub until embeddings added)

Usage:
    engine = MemoryDecayEngine()
    score = engine.score(memory, query_text)
"""
from __future__ import annotations

import math
import time
from typing import Protocol


class _MemoryLike(Protocol):
    importance: float
    last_accessed: float
    content: str


class MemoryDecayEngine:
    """
    Scores a memory for retrieval using the Ebbinghaus forgetting curve.

    decay_factor controls how fast recency falls off.
    Default half-life ≈ 1 hour (factor = 0.99 per elapsed hour).
    """

    def __init__(self, decay_factor: float = 0.99) -> None:
        if not 0.0 < decay_factor < 1.0:
            raise ValueError("decay_factor must be in (0, 1)")
        self._decay = decay_factor

    def recency_score(self, last_accessed: float) -> float:
        hours_elapsed = (time.time() - last_accessed) / 3600
        return float(self._decay ** hours_elapsed)

    def importance_score(self, memory: _MemoryLike) -> float:
        return memory.importance / 10.0

    def relevance_score(self, memory: _MemoryLike, query: str) -> float:
        """
        Keyword-overlap relevance (stub).
        ponytail: replace with embedding cosine similarity when vector store is added.
        """
        query_words = set(query.lower().split())
        content_words = set(memory.content.lower().split())
        if not query_words:
            return 0.0
        overlap = len(query_words & content_words)
        return overlap / math.sqrt(len(query_words) * max(len(content_words), 1))

    def score(self, memory: _MemoryLike, query: str = "") -> float:
        """
        Composite retrieval score in [0, 1].
        Accepts any object with .importance, .last_accessed, .content fields
        (both Memory and MemoryRecord qualify).
        Weights mirror the original Gen_Agent legacy implementation.
        """
        r = self.recency_score(memory.last_accessed)
        i = self.importance_score(memory)
        v = self.relevance_score(memory, query)
        return (r + i + v) / 3.0

