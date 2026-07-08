#!/usr/bin/env python3
"""
Minimal legacy Gen_Agent blocking simulation for A/B comparison.
Uses legacy SimEngine directly (no NSGS, no full report pipeline).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

LEGACY = Path(__file__).resolve().parent.parent.parent / "Gen_Agent"
OUT = Path(__file__).resolve().parent.parent / "output" / "sim_blocking_100_legacy.json"

if str(LEGACY) not in sys.path:
    sys.path.insert(0, str(LEGACY))

os.environ.setdefault("GEN_AGENT_ENABLE_STANFORD_WORKER", "0")
os.environ.setdefault("OLLAMA_MODEL", "llama3.2:3b")
os.environ.setdefault("OLLAMA_TIMEOUT", "300")


def main() -> int:
    from core.sim.sim_engine import SimConfig, SimEngine

    ticks = int(os.getenv("SIM_TICKS", "100"))
    t0 = time.perf_counter()

    cfg = SimConfig(
        width=20,
        height=20,
        seed=42,
        tick_hz=10.0,
        agent_count=5,
        agent_names=["Marco", "Lucia", "Giovanni", "Anna", "Elena"],
        interaction_radius=5,
        interaction_every_ticks=10,
        interaction_min_gap_ticks=32,
        missions_enabled=True,
        block_on_dialogue=True,
        dialogue_wait_timeout_seconds=300.0,
        dialogue_memory_limit=3,
        memory_decay_db_interval_ticks=9999,
        memory_consolidation_interval_ticks=9999,
    )
    engine = SimEngine(cfg)

    # Place all agents near centre (same trick as new project)
    if len(engine.agents) >= 2:
        for i, ag in enumerate(engine.agents):
            import math
            angle = (2 * math.pi * i) / len(engine.agents)
            x = 10.0 + 1.2 * math.cos(angle)
            y = 10.0 + 1.2 * math.sin(angle)
            ag.pos = (int(x), int(y))
            ag.pos_f = (x, y)
            ag.target_cell = None

    errors: list[str] = []
    dialogue_log: list[dict] = []

    for tick_num in range(1, ticks + 1):
        try:
            engine.step()
            # Legacy stores events differently — check runtime state
            rs = engine.runtime_state() if hasattr(engine, "runtime_state") else {}
            events = rs.get("last_events", []) if isinstance(rs, dict) else []
            for ev in events:
                if isinstance(ev, dict) and ev.get("dialogue"):
                    dialogue_log.append({"tick": tick_num, "event": str(ev)[:120]})
                    print(f"[tick {tick_num:3d}] dialogue event", flush=True)
            if tick_num % 25 == 0:
                print(f"  ... tick {tick_num}/{ticks}", flush=True)
        except Exception as exc:
            errors.append(f"tick {tick_num}: {exc!r}")
            print(f"ERROR tick {tick_num}: {exc!r}", flush=True)

    elapsed = time.perf_counter() - t0
    engine.stop()

    rs = engine.runtime_state() if hasattr(engine, "runtime_state") else {}
    stats = rs.get("stats", rs) if isinstance(rs, dict) else {}

    summary = {
        "project": "Gen_Agent (legacy minimal)",
        "scenario": "blocking_balanced",
        "llm": "ollama",
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        "ticks_requested": ticks,
        "final_tick": rs.get("tick", ticks) if isinstance(rs, dict) else ticks,
        "agents": 5,
        "block_on_dialogue": True,
        "interaction_radius": 5,
        "interaction_every_ticks": 10,
        "min_gap_ticks": 32,
        "interactions": stats.get("interactions", rs.get("interactions", 0) if isinstance(rs, dict) else 0),
        "dialogues": stats.get("dialogues", rs.get("dialogues", 0) if isinstance(rs, dict) else 0),
        "dialogue_utterances": stats.get("dialogue_utterances", 0),
        "real_time_sec": round(elapsed, 2),
        "avg_sec_per_tick": round(elapsed / max(ticks, 1), 3),
        "dialogue_log": dialogue_log,
        "errors": errors,
        "runtime_state_keys": list(rs.keys()) if isinstance(rs, dict) else [],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n=== LEGACY RESULT ===", flush=True)
    for k, v in summary.items():
        if k not in ("dialogue_log", "errors", "runtime_state_keys"):
            print(f"{k}: {v}", flush=True)
    print(f"Report: {OUT}", flush=True)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
