#!/usr/bin/env python3
"""
Simulation with local Ollama LLM — real dialogue generation.

Requirements:
    - Ollama installed (https://ollama.com)
    - Model pulled: ollama pull llama3.2:3b

If Ollama is not available, falls back to mock automatically.

Usage:
    python examples/ollama_simple.py
    OLLAMA_MODEL=llama3.1:8b python examples/ollama_simple.py
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

AGENTS = ["Marco", "Lucia", "Giovanni"]
TICKS = 20
REPORT_PATH = ROOT / "output" / "ollama_simple.json"


def _preflight_check(model: str) -> bool:
    """Verify Ollama is up and can generate before starting the simulation."""
    from gen_agent.llm.ollama_provider import OllamaProvider
    provider = OllamaProvider(model=model, timeout=10)
    if not provider.is_available():
        print("  [pre-flight] Ollama API not reachable — falling back to mock.")
        return False
    print(f"  [pre-flight] Ollama up. Testing generation with {model}...")
    result = provider.complete("Reply with exactly one word: OK")
    if "[" in result and ("error" in result.lower() or "unavailable" in result.lower()):
        print(f"  [pre-flight] Generation failed ({result[:60]}) — falling back to mock.")
        return False
    print(f"  [pre-flight] OK — model responded: {result[:40]!r}")
    return True


def main() -> None:
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    os.environ.setdefault("OLLAMA_TIMEOUT", "60")

    print(f"=== ollama_simple — {len(AGENTS)} agents, {TICKS} ticks ===")
    print(f"  Model: {model}\n")

    # Pre-flight: if Ollama is down, use mock so the script still completes
    ollama_ok = _preflight_check(model)
    llm_provider_name = "ollama" if ollama_ok else "mock"
    os.environ["LLM_PROVIDER"] = llm_provider_name
    os.environ["OLLAMA_MODEL"] = model

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
        seed=42,
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
        "example": "ollama_simple",
        "llm_used": llm_provider_name,
        "model": model if ollama_ok else "mock",
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
    print(f"  LLM      : {llm_provider_name} ({model if ollama_ok else 'mock'})")
    print(f"  Dialogues: {stats['dialogues']}")
    print(f"  Memories : {memory.count()}")
    print(f"  Time     : {elapsed:.1f}s")
    print(f"  Report   : {REPORT_PATH}")


if __name__ == "__main__":
    main()
