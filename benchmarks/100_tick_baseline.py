"""
Benchmark: 100-tick baseline (3 agents, stub mode, no LLM).

Measures tick advancement time and ticks/s throughput.
JSON output saved to output/benchmarks/.

Usage:
    python benchmarks/100_tick_baseline.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks._common import make_meta, save_result, simple_engine

TICKS = 100
N_AGENTS = 3
PRESET = "100_tick_baseline"


def run() -> dict:
    engine = simple_engine(n_agents=N_AGENTS)
    t0 = time.perf_counter()
    for _ in range(TICKS):
        engine.advance()
    elapsed = time.perf_counter() - t0

    stats = engine.stats()
    result = {
        "meta": make_meta(PRESET),
        "ticks": TICKS,
        "n_agents": N_AGENTS,
        "elapsed_s": round(elapsed, 4),
        "ticks_per_sec": round(TICKS / elapsed, 2),
        "ms_per_tick": round(elapsed / TICKS * 1000, 3),
        "engine_stats": stats,
    }
    print(f"[100_tick_baseline] {TICKS} ticks / {elapsed:.3f}s "
          f"= {result['ticks_per_sec']} tick/s")
    return result


if __name__ == "__main__":
    save_result(PRESET, run())
