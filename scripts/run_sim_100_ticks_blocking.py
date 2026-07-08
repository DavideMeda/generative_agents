#!/usr/bin/env python3
"""
Run a 100-tick simulation with 5 agents and blocking dialogues.

Modes:
  --llm mock    offline, no network (default for CI)
  --llm ollama  real Ollama blocking dialogues (uses scenarios/blocking_100.py)

Usage (from repo root):
  set OLLAMA_MODEL=gemma4:12b
  python scripts/run_sim_100_ticks_blocking.py --llm ollama
  python scripts/run_sim_100_ticks_blocking.py --llm mock --ticks 100
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_AGENT_NAMES = ["Marco", "Lucia", "Giovanni", "Anna", "Elena"]


def run_ollama_scenario(ticks: int, report_path: Path | None) -> dict:
    """Full modular stack: World + POI + Missions + Ollama + blocking dialogues."""
    from config.scenario import load_scenario

    os.environ.setdefault("LLM_PROVIDER", "ollama")
    os.environ.setdefault("OLLAMA_MODEL", "llama3.2:3b")
    os.environ.setdefault("OLLAMA_TIMEOUT", "300")
    scenario = load_scenario("blocking_100")
    scenario.sim_config.block_on_dialogue = True

    print(f"LLM provider: ollama  model: {os.getenv('OLLAMA_MODEL', 'llama3.2:3b')}", flush=True)
    print(f"Agents: {scenario.agent_names}", flush=True)
    print(f"World POIs: {len(scenario.world.pois)}", flush=True)
    print(
        f"Params: radius={scenario.sim_config.interaction_radius} "
        f"every={scenario.sim_config.interaction_every_ticks} "
        f"min_gap={scenario.sim_config.min_gap_ticks}",
        flush=True,
    )

    engine = scenario.build_engine()

    # Start agents near Park centre so first interaction window can trigger dialogues
    # (legacy blocking_balanced also converges agents via POI navigation)
    import math
    park_x, park_y = 10.0, 10.0
    for idx, (aid, state) in enumerate(engine._agents.items()):  # type: ignore[attr-defined]
        angle = (2 * math.pi * idx) / max(len(scenario.agent_names), 1)
        state.position = (park_x + 1.2 * math.cos(angle), park_y + 1.2 * math.sin(angle))

    memory = engine._memory  # type: ignore[attr-defined]
    errors: list[str] = []
    dialogue_log: list[dict] = []
    t0 = time.perf_counter()

    for tick_num in range(1, ticks + 1):
        try:
            result = engine.advance()
            for event in result.events:
                if event.get("type") == "interaction" and event.get("dialogue"):
                    d = event["dialogue"]
                    entry = {
                        "tick": result.tick,
                        "agents": event.get("agent_names"),
                        "turns": d.get("turns"),
                        "elapsed_sec": d.get("elapsed_sec"),
                        "preview": d.get("transcript_preview", "")[:120],
                    }
                    dialogue_log.append(entry)
                    print(
                        f"[tick {result.tick:3d}] dialogue {entry['agents']} "
                        f"turns={entry['turns']} elapsed={entry['elapsed_sec']}s",
                        flush=True,
                    )
            if tick_num % 25 == 0:
                stats = engine.stats()
                print(
                    f"  ... tick {tick_num}/{ticks} | "
                    f"interactions={stats['interactions']} "
                    f"dialogues={stats['dialogues']} "
                    f"missions_done={stats.get('missions_completed', 0)}"
                )
        except Exception as exc:
            errors.append(f"tick {tick_num}: {exc!r}")
            print(f"ERROR tick {tick_num}: {exc!r}")

    elapsed = time.perf_counter() - t0
    stats = engine.stats()
    snap = engine.snapshot()

    summary = {
        "project": "Nuovo Gen_Agent (modular)",
        "scenario": "blocking_100",
        "llm": os.getenv("LLM_PROVIDER", "ollama"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        "ticks_requested": ticks,
        "final_tick": snap["tick"],
        "agents": len(scenario.agent_names),
        "agent_names": scenario.agent_names,
        "block_on_dialogue": True,
        "interaction_radius": scenario.sim_config.interaction_radius,
        "interaction_every_ticks": scenario.sim_config.interaction_every_ticks,
        "min_gap_ticks": scenario.sim_config.min_gap_ticks,
        "world_pois": len(scenario.world.pois),
        "missions_enabled": scenario.enable_missions,
        "interactions": stats["interactions"],
        "dialogues": stats["dialogues"],
        "dialogue_utterances": stats["dialogue_utterances"],
        "missions_completed": stats.get("missions_completed", 0),
        "memories_total": memory.count() if memory else 0,
        "real_time_sec": round(elapsed, 2),
        "avg_sec_per_tick": round(elapsed / max(ticks, 1), 3),
        "dialogue_log": dialogue_log,
        "errors": errors,
    }

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nReport saved: {report_path}")

    return summary


def run_mock_simple(ticks: int, agent_names: list[str], **kwargs) -> dict:
    """Legacy simple path (random walk, no POI) for fast offline smoke test."""
    from gen_agent.dialogue.dialogue_engine import DialogueEngine
    from gen_agent.interfaces.sim_protocol import AgentConfig
    from gen_agent.memory.manager import MemoryManager
    from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend
    from gen_agent.sim.engine import SimConfig, SimEngine
    import math

    backend = SQLiteMemoryBackend(db_path=":memory:")
    memory = MemoryManager(backend=backend)
    dialogue = DialogueEngine(llm=None, memory_store=memory, max_turns=4)

    cfg = SimConfig(
        interaction_radius=kwargs.get("radius", 4.0),
        min_gap_ticks=kwargs.get("min_gap", 3),
        interaction_every_ticks=kwargs.get("every", 4),
        block_on_dialogue=True,
        dialogue_max_turns=4,
        random_walk_step=0.3,
        seed=42,
    )
    engine = SimEngine(config=cfg, dialogue_engine=dialogue, memory_store=memory)

    for idx, name in enumerate(agent_names):
        angle = (2 * math.pi * idx) / max(len(agent_names), 1)
        pos = (1.5 * math.cos(angle), 1.5 * math.sin(angle))
        engine.register_agent(AgentConfig(agent_id=f"a{idx+1}", name=name, position=pos))

    t0 = time.perf_counter()
    errors: list[str] = []
    for tick_num in range(1, ticks + 1):
        try:
            engine.advance()
        except Exception as exc:
            errors.append(f"tick {tick_num}: {exc!r}")

    elapsed = time.perf_counter() - t0
    stats = engine.stats()
    return {
        "project": "Nuovo Gen_Agent (mock simple)",
        "ticks_requested": ticks,
        "agents": len(agent_names),
        "block_on_dialogue": True,
        "interactions": stats["interactions"],
        "dialogues": stats["dialogues"],
        "dialogue_utterances": stats["dialogue_utterances"],
        "memories_total": memory.count(),
        "real_time_sec": round(elapsed, 2),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="100-tick blocking dialogue simulation")
    parser.add_argument("--ticks", type=int, default=100)
    parser.add_argument("--agents", type=int, default=5)
    parser.add_argument("--llm", choices=["mock", "ollama"], default="ollama")
    parser.add_argument("--report", type=str, default="output/sim_blocking_100_new.json")
    args = parser.parse_args()

    print("=== Nuovo Gen_Agent — blocking simulation ===")
    print(f"ticks={args.ticks} agents={args.agents} llm={args.llm}")

    if args.llm == "ollama":
        summary = run_ollama_scenario(args.ticks, Path(args.report))
    else:
        names = DEFAULT_AGENT_NAMES[: args.agents]
        summary = run_mock_simple(args.ticks, names)

    print("\n=== RESULT ===")
    for key, value in summary.items():
        if key not in ("dialogue_log", "errors"):
            print(f"{key}: {value}")

    if summary.get("errors"):
        print("\nFAILED — exceptions during ticks:", summary["errors"])
        return 1
    if summary.get("dialogues", 0) == 0:
        print("\nWARNING — no dialogues (agents may not have met; try lower min_gap)")
        return 2
    print("\nOK — simulation completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
