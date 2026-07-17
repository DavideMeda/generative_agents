#!/usr/bin/env python3
"""
Demonstration of cognitive bias layers — no LLM required.

Shows how ConfirmationBias, AvailabilityHeuristic, AnchoringBias, and
RecencyBias influence agent interaction probability and dialogue intent.

Usage:
    python examples/cognitive_biases.py
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["ENABLE_BIASES"] = "true"

AGENTS = ["Alice", "Bob", "Carol", "David", "Eve"]
TICKS = 30


def main() -> None:
    from gen_agent.cognitive.biases import (  # noqa: E402
        AnchoringBias,
        AvailabilityHeuristic,
        BiasLayer,
        ConfirmationBias,
        RecencyBias,
    )
    from gen_agent.dialogue.dialogue_engine import DialogueEngine  # noqa: E402
    from gen_agent.interfaces.sim_protocol import AgentConfig  # noqa: E402
    from gen_agent.memory.manager import MemoryManager  # noqa: E402
    from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend  # noqa: E402
    from gen_agent.sim.engine import SimConfig, SimEngine  # noqa: E402

    print("=== cognitive_biases — bias layer demo ===\n")

    # 1. ConfirmationBias: filter memories by keyword overlap with a belief
    cb = ConfirmationBias(threshold=0.2)
    memories = [
        {"content": "Alice talked about the park and outdoor activities"},
        {"content": "Bob mentioned he loves the library and quiet study"},
        {"content": "The park is a great place for social meetups outdoor"},
    ]
    belief = "park outdoor activities"
    filtered = cb.filter(belief, memories)
    print("ConfirmationBias (threshold=0.20):")
    print(f"  Belief: {belief!r}")
    print(f"  Memories in: {len(memories)}  ->  kept: {len(filtered)}")
    for m in filtered:
        print(f"    + {m['content'][:60]}")

    # 2. AvailabilityHeuristic: frequent events inflate estimated probability
    ah = AvailabilityHeuristic(window_size=10)
    for _ in range(7):
        ah.record("dialogue")
    for _ in range(1):
        ah.record("mission")
    print("\nAvailabilityHeuristic (window=10):")
    print(f"  'dialogue' (7 records) -> P = {ah.estimated_probability('dialogue'):.2f}  (inflated)")
    print(f"  'mission'  (1 record)  -> P = {ah.estimated_probability('mission'):.2f}")

    # 3. AnchoringBias: first estimate sticks, later values pulled toward it
    anchor = AnchoringBias(anchor_weight=0.3)
    v1 = anchor.observe("a1", 0.4)
    v2 = anchor.observe("a1", 0.9)
    v3 = anchor.observe("a1", 0.1)
    print("\nAnchoringBias (anchor_weight=0.3, anchor=0.40):")
    print(f"  observe(0.40) -> {v1:.3f}  (first: sets anchor)")
    print(f"  observe(0.90) -> {v2:.3f}  (pulled down toward anchor)")
    print(f"  observe(0.10) -> {v3:.3f}  (pulled up toward anchor)")

    # 4. RecencyBias: memory weight decays with age
    rb = RecencyBias(decay_lambda=0.2)
    print("\nRecencyBias (lambda=0.20):")
    for age in [0, 5, 10, 20]:
        print(f"  age={age:2d} ticks -> weight={rb.weight(age):.3f}")

    # 5. BiasLayer facade: combined willingness modifier used by SimEngine
    bias_layer = BiasLayer()
    for _ in range(5):
        bias_layer.availability.record("dialogue")
    w = bias_layer.willingness_modifier("a1", current_tick=20, last_interaction_tick=15)
    print(f"\nBiasLayer.willingness_modifier (tick=20, last_interaction=15) -> {w:.3f}")

    # 6. Short simulation with biases active
    print(f"\n--- {TICKS}-tick simulation with ENABLE_BIASES=true ---")

    backend = SQLiteMemoryBackend(db_path=":memory:")
    memory = MemoryManager(backend=backend)
    dialogue = DialogueEngine(llm=None, memory_store=memory, max_turns=2)

    cfg = SimConfig(
        tick_interval_sec=0.0,
        interaction_radius=4.0,
        min_gap_ticks=4,
        block_on_dialogue=True,
        dialogue_max_turns=2,
        random_walk_step=0.3,
        missions_enabled=False,
        seed=42,
    )
    engine = SimEngine(config=cfg, dialogue_engine=dialogue, memory_store=memory)

    for idx, name in enumerate(AGENTS):
        angle = (2 * math.pi * idx) / len(AGENTS)
        pos = (2.0 * math.cos(angle), 2.0 * math.sin(angle))
        engine.register_agent(AgentConfig(agent_id=f"a{idx+1}", name=name, position=pos))

    for tick_num in range(1, TICKS + 1):
        result = engine.advance()
        if result.events:
            for event in result.events:
                if event.get("type") == "interaction":
                    print(f"  tick {tick_num:2d}  {' & '.join(event.get('agent_names', []))}")

    stats = engine.stats()
    print("\n--- Final stats ---")
    print(f"  Interactions: {stats['interactions']}")
    print(f"  Dialogues   : {stats['dialogues']}")
    print(f"  Memories    : {memory.count()}")
    print(f"\nBias layers active: ENABLE_BIASES={os.getenv('ENABLE_BIASES')}")
    print("See gen_agent/cognitive/biases.py for implementation details.")


if __name__ == "__main__":
    main()
