"""
Benchmark: agent scaling profile.

Measures how tick time grows as the number of agents increases.
Scales from 1 to 50 agents, 20 ticks each.

Usage:
    python benchmarks/agent_scaling_profile.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks._common import make_meta, save_result, simple_engine

TICKS_PER_RUN = 20
AGENT_COUNTS = [1, 2, 5, 10, 20, 50]
PRESET = "agent_scaling_profile"


def run() -> dict:
    samples: list[dict] = []
    for n in AGENT_COUNTS:
        engine = simple_engine(n_agents=n)
        t0 = time.perf_counter()
        for _ in range(TICKS_PER_RUN):
            engine.advance()
        elapsed = time.perf_counter() - t0
        ms_per_tick = elapsed / TICKS_PER_RUN * 1000
        samples.append({
            "n_agents": n,
            "ticks": TICKS_PER_RUN,
            "elapsed_s": round(elapsed, 4),
            "ms_per_tick": round(ms_per_tick, 3),
        })
        print(f"  n_agents={n:3d}  ms/tick={ms_per_tick:.3f}")

    result = {
        "meta": make_meta(PRESET),
        "ticks_per_run": TICKS_PER_RUN,
        "samples": samples,
    }
    return result


if __name__ == "__main__":
    print(f"[agent_scaling_profile] running scaling test ({AGENT_COUNTS} agents)")
    save_result(PRESET, run())
