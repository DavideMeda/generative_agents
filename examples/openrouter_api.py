#!/usr/bin/env python3
"""
Simulation with OpenRouter cloud API — no local model required.

Requirements:
    - Free API key from https://openrouter.ai
    - Default free model: qwen/qwen3-235b-a22b:free

Usage:
    # Set key via environment variable (recommended)
    export OPENROUTER_API_KEY=sk-or-...
    python examples/openrouter_api.py

    # Or pass inline (Linux/macOS)
    OPENROUTER_API_KEY=sk-or-... python examples/openrouter_api.py

    # Custom model
    OPENROUTER_MODEL=openai/gpt-4o-mini python examples/openrouter_api.py

If the API key is missing, falls back to mock LLM automatically.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AGENTS = ["Sophia", "Marcus", "Lena"]
TICKS = 20
REPORT_PATH = ROOT / "output" / "openrouter_simple.json"

_FREE_MODELS = [
    "qwen/qwen3-235b-a22b:free",
    "mistralai/mistral-7b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]


def _check_api_key() -> str | None:
    """Return API key from env, or None with a helpful message."""
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("  [pre-flight] OPENROUTER_API_KEY not set.")
        print("  Get a free key at https://openrouter.ai → falling back to mock.")
        print()
        print("  To use OpenRouter:")
        print("    export OPENROUTER_API_KEY=sk-or-...")
        print("    python examples/openrouter_api.py")
        return None
    return key


def main() -> None:
    model = os.getenv("OPENROUTER_MODEL", _FREE_MODELS[0])
    api_key = _check_api_key()

    print(f"=== openrouter_api — {len(AGENTS)} agents, {TICKS} ticks ===")

    if api_key:
        print(f"  Model: {model}")
        print(f"  Key  : {api_key[:8]}...{api_key[-4:]}\n")
        os.environ["LLM_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = api_key
        os.environ["OPENROUTER_MODEL"] = model
        os.environ.setdefault("OPENROUTER_TIMEOUT", "60")
        llm_provider_name = "openrouter"
    else:
        print("  Using mock LLM (no API key)\n")
        os.environ["LLM_PROVIDER"] = "mock"
        llm_provider_name = "mock"

    from gen_agent.dialogue.dialogue_engine import DialogueEngine
    from gen_agent.interfaces.sim_protocol import AgentConfig
    from gen_agent.llm.provider import get_llm_provider
    from gen_agent.memory.manager import MemoryManager
    from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend
    from gen_agent.sim.engine import SimConfig, SimEngine

    backend = SQLiteMemoryBackend(db_path=":memory:")
    memory = MemoryManager(backend=backend)

    provider = get_llm_provider(llm_provider_name)
    dialogue = DialogueEngine(
        llm=provider.complete,
        memory_store=memory,
        max_turns=2,
        min_words=15,
        max_attempts=2,
    )

    cfg = SimConfig(
        tick_interval_sec=0.0,
        interaction_radius=3.5,
        min_gap_ticks=8,
        block_on_dialogue=True,
        dialogue_max_turns=2,
        random_walk_step=0.2,
        missions_enabled=False,
        seed=7,
    )
    engine = SimEngine(config=cfg, dialogue_engine=dialogue, memory_store=memory)

    for idx, name in enumerate(AGENTS):
        angle = (2 * math.pi * idx) / len(AGENTS)
        pos = (1.8 * math.cos(angle), 1.8 * math.sin(angle))
        engine.register_agent(AgentConfig(agent_id=f"a{idx+1}", name=name, position=pos))

    dialogue_log: list[dict] = []
    t0 = time.perf_counter()

    for tick_num in range(1, TICKS + 1):
        result = engine.advance()
        for event in result.events:
            if event.get("type") == "interaction" and event.get("dialogue"):
                d = event["dialogue"]
                entry = {
                    "tick": result.tick,
                    "agents": event.get("agent_names"),
                    "turns": d.get("turns"),
                    "elapsed_sec": round(d.get("elapsed_sec", 0), 2),
                    "preview": d.get("transcript_preview", "")[:100],
                }
                dialogue_log.append(entry)
                print(f"  [tick {tick_num:2d}] dialogue {entry['agents']} "
                      f"turns={entry['turns']} ({entry['elapsed_sec']}s)")
                print(f"    {entry['preview'][:80]}")

    elapsed = time.perf_counter() - t0
    stats = engine.stats()

    report = {
        "example": "openrouter_api",
        "llm_used": llm_provider_name,
        "model": model if api_key else "mock",
        "ticks": TICKS,
        "agents": AGENTS,
        "interactions": stats["interactions"],
        "dialogues": stats["dialogues"],
        "dialogue_utterances": stats["dialogue_utterances"],
        "memories_total": memory.count(),
        "real_time_sec": round(elapsed, 2),
        "dialogue_log": dialogue_log,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print("\n--- Final stats ---")
    print(f"  LLM      : {llm_provider_name} ({model if api_key else 'mock'})")
    print(f"  Dialogues: {stats['dialogues']}")
    print(f"  Memories : {memory.count()}")
    print(f"  Time     : {elapsed:.1f}s")
    print(f"  Report   : {REPORT_PATH}")
    if not api_key:
        print("\n  Tip: set OPENROUTER_API_KEY to get real LLM dialogues.")
        print(f"  Free models: {', '.join(_FREE_MODELS)}")


if __name__ == "__main__":
    main()
