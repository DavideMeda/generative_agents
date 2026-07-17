#!/usr/bin/env python3
"""
Minimal simulation — no LLM, no network, runs in ~5 seconds.

Three agents walk around a small town, meet at POIs, form memories.
Perfect first contact with the new-gen-agent API.

Usage:
    python examples/hello_world.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gen_agent.dialogue.dialogue_engine import DialogueEngine  # noqa: E402
from gen_agent.interfaces.sim_protocol import AgentConfig  # noqa: E402
from gen_agent.memory.manager import MemoryManager  # noqa: E402
from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend  # noqa: E402
from gen_agent.sim.engine import SimConfig, SimEngine  # noqa: E402

AGENTS = ["Alice", "Bob", "Carol"]
TICKS = 10


def main() -> None:
    # In-memory SQLite — no file created, discarded after script ends
    backend = SQLiteMemoryBackend(db_path=":memory:")
    memory = MemoryManager(backend=backend)

    # Mock LLM: DialogueEngine with llm=None uses built-in fallback phrases
    dialogue = DialogueEngine(llm=None, memory_store=memory, max_turns=3)

    cfg = SimConfig(
        tick_interval_sec=0.0,      # no real-time delay
        interaction_radius=3.0,
        min_gap_ticks=3,
        block_on_dialogue=True,
        dialogue_max_turns=3,
        random_walk_step=0.3,
        missions_enabled=False,
        seed=42,
    )
    engine = SimEngine(config=cfg, dialogue_engine=dialogue, memory_store=memory)

    # Place agents in a circle so they start close enough to interact
    for idx, name in enumerate(AGENTS):
        angle = (2 * math.pi * idx) / len(AGENTS)
        pos = (1.5 * math.cos(angle), 1.5 * math.sin(angle))
        engine.register_agent(AgentConfig(agent_id=f"a{idx+1}", name=name, position=pos))

    print(f"=== hello_world — {len(AGENTS)} agents, {TICKS} ticks, mock LLM ===\n")

    for tick_num in range(1, TICKS + 1):
        result = engine.advance()
        for event in result.events:
            if event.get("type") == "interaction":
                agents_str = " & ".join(event.get("agent_names", []))
                print(f"  tick {tick_num:2d}  interaction: {agents_str}")

    stats = engine.stats()
    snap = engine.snapshot()

    print(f"\n--- Final stats after {TICKS} ticks ---")
    print(f"  Interactions : {stats['interactions']}")
    print(f"  Dialogues    : {stats['dialogues']}")
    print(f"  Memories     : {memory.count()}")
    print(f"  Final tick   : {snap['tick']}")
    print("\nDone. Try 'python examples/ollama_simple.py' for real LLM dialogues.")


if __name__ == "__main__":
    main()
