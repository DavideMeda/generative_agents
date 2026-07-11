"""
Benchmark: memory retrieval performance.

Inserisce N memorie in SQLite e misura il tempo di retrieval
per varie dimensioni del corpus.

Uso:
    python benchmarks/memory_retrieval_benchmark.py
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks._common import make_meta, save_result

PRESET = "memory_retrieval_benchmark"
MEMORY_SIZES = [10, 50, 100, 500]
QUERIES_PER_SIZE = 20


def run() -> dict:
    from gen_agent.interfaces.memory_protocol import MemoryQuery
    from gen_agent.memory.manager import MemoryManager

    samples: list[dict] = []

    for n_memories in MEMORY_SIZES:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = MemoryManager(data_dir=tmpdir)

            # Inserimento
            t_insert = time.perf_counter()
            for i in range(n_memories):
                mgr.store(
                    agent_id="agent_0",
                    content=f"Memory {i}: went to the park and talked with friend {i % 5}",
                    memory_type="event",
                    importance=float(i % 10) / 10.0,
                    tick=i,
                )
            insert_elapsed = time.perf_counter() - t_insert

            # Retrieval
            q = MemoryQuery(agent_id="agent_0", query_text="park friend", top_k=5)
            t_query = time.perf_counter()
            for _ in range(QUERIES_PER_SIZE):
                mgr.retrieve(q)
            query_elapsed = time.perf_counter() - t_query

        ms_per_query = query_elapsed / QUERIES_PER_SIZE * 1000
        samples.append({
            "n_memories": n_memories,
            "insert_elapsed_s": round(insert_elapsed, 4),
            "queries": QUERIES_PER_SIZE,
            "total_query_elapsed_s": round(query_elapsed, 4),
            "ms_per_query": round(ms_per_query, 3),
        })
        print(f"  n_memories={n_memories:4d}  ms/query={ms_per_query:.3f}")

    result = {
        "meta": make_meta(PRESET),
        "queries_per_size": QUERIES_PER_SIZE,
        "samples": samples,
    }
    return result


if __name__ == "__main__":
    print(f"[memory_retrieval_benchmark] sizes={MEMORY_SIZES}")
    save_result(PRESET, run())
