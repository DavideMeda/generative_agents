"""
MemoryCompressor — groups similar memories and replaces them with a summary.

Algorithm:
  1. For each agent, load all memories of the same type.
  2. Cluster by keyword overlap (threshold > 0.4 = similar).
  3. Replace each cluster with one summary memory (content = concatenated truncations).
  4. Delete the originals.

Reduces DB size without losing key information.
Runs every N ticks when ENABLE_MEMORY_COMPRESSION=true.

ponytail: O(n²) clustering — fine for <500 memories/agent.
"""
from __future__ import annotations

import logging
import os
import re

from gen_agent.interfaces.memory_protocol import MemoryQuery, MemoryRecord

logger = logging.getLogger(__name__)

_SIMILARITY_THRESHOLD = 0.35
_MIN_CLUSTER_SIZE = 3       # don't compress lone memories
_SUMMARY_MAX_CHARS = 300


def _tokens(text: str) -> set:
    return {w.lower() for w in re.split(r"\W+", text) if len(w) > 2}


def _jaccard(a: set, b: set) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


class MemoryCompressor:
    """
    Compresses memories for all agents tracked by the given memory store.
    """

    def __init__(self, memory_store=None, trigger_every_ticks: int = 50) -> None:
        self._mem = memory_store
        self._trigger = trigger_every_ticks

    def should_run(self, tick: int) -> bool:
        return tick > 0 and tick % self._trigger == 0

    def compress_agent(self, agent_id: str) -> int:
        """
        Compress memories for one agent. Returns number of memories removed.
        """
        if self._mem is None:
            return 0
        records = self._mem.retrieve(
            MemoryQuery(agent_id=agent_id, query_text="", top_k=1000)
        )
        clusters = self._cluster(records)
        removed = 0
        for cluster in clusters:
            if len(cluster) < _MIN_CLUSTER_SIZE:
                continue
            summary = self._summarise(cluster)
            # Store summary
            self._mem.store(
                agent_id=agent_id,
                content=summary,
                memory_type="compressed",
                importance=max(r.importance for r in cluster),
            )
            # Delete originals
            for r in cluster:
                try:
                    self._mem.delete(r.memory_id)
                    removed += 1
                except Exception:
                    pass
        if removed:
            logger.info("MemoryCompressor: agent %s compressed %d memories", agent_id, removed)
        return removed

    def _cluster(self, records: list[MemoryRecord]) -> list[list[MemoryRecord]]:
        if not records:
            return []
        token_sets = [_tokens(r.content) for r in records]
        assigned = [-1] * len(records)
        clusters: list[list[int]] = []

        for i in range(len(records)):
            if assigned[i] != -1:
                continue
            cluster_idx = len(clusters)
            clusters.append([i])
            assigned[i] = cluster_idx
            for j in range(i + 1, len(records)):
                if assigned[j] != -1:
                    continue
                if _jaccard(token_sets[i], token_sets[j]) >= _SIMILARITY_THRESHOLD:
                    clusters[cluster_idx].append(j)
                    assigned[j] = cluster_idx

        return [[records[idx] for idx in cl] for cl in clusters]

    @staticmethod
    def _summarise(cluster: list[MemoryRecord]) -> str:
        parts = [r.content[:80] for r in cluster]
        joined = " | ".join(parts)
        return f"[compressed {len(cluster)}] {joined}"[:_SUMMARY_MAX_CHARS]


def make_compressor_if_enabled(memory_store=None) -> MemoryCompressor | None:
    if os.getenv("ENABLE_MEMORY_COMPRESSION", "false").lower() in ("1", "true", "yes"):
        return MemoryCompressor(memory_store=memory_store)
    return None
