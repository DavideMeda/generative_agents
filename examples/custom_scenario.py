#!/usr/bin/env python3
"""
Template for building a custom scenario from scratch.

This example creates a "party planning" scenario: 4 neighbors who meet at a
community center to organize a block party. It demonstrates:
  - Custom world layout with your own POIs
  - Custom agent names and starting positions
  - Tweaking SimConfig parameters for your use case
  - Using Scenario.from_profile() as an alternative to manual wiring

Usage:
    python examples/custom_scenario.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Step 1: Define your world ────────────────────────────────────────────────
# A World holds Points of Interest (POIs). Agents navigate toward them
# autonomously when a MissionSystem assigns a visit goal.

from gen_agent.world.poi import POI  # noqa: E402
from gen_agent.world.world import World  # noqa: E402


def build_party_world() -> World:
    """Small neighborhood: community center, backyards, park, grocery store."""
    return World(
        width=15.0,
        height=15.0,
        pois=[
            POI("community_center", "Community Center",  7.5, 7.5,  ["social", "meeting"]),
            POI("backyard_a",       "Backyard A",        2.0, 2.0,  ["rest", "private"]),
            POI("backyard_b",       "Backyard B",        2.0, 13.0, ["rest", "private"]),
            POI("backyard_c",       "Backyard C",        13.0, 2.0, ["rest", "private"]),
            POI("backyard_d",       "Backyard D",        13.0, 13.0,["rest", "private"]),
            POI("park",             "Neighborhood Park", 7.5, 2.5,  ["social", "outdoor"]),
            POI("grocery",          "Grocery Store",     2.5, 7.5,  ["social", "shopping"]),
        ],
    )


# ── Step 2: Define your scenario ─────────────────────────────────────────────
# A Scenario bundles agent names, world, SimConfig, and LLM provider.

from config.scenario import Scenario  # noqa: E402
from gen_agent.sim.engine import SimConfig  # noqa: E402


def build_party_scenario() -> Scenario:
    return Scenario(
        name="party_planning",
        description=(
            "Four neighbors in a small cul-de-sac plan a block party. "
            "They wander between their backyards, the park, and the community center."
        ),
        agent_names=["Nina", "Tom", "Sara", "Ravi"],
        world=build_party_world(),
        sim_config=SimConfig(
            tick_interval_sec=0.0,          # no real-time delay (fast mode)
            interaction_radius=3.0,         # must be within 3.0 units to interact
            min_gap_ticks=5,                # minimum ticks between two interactions
            block_on_dialogue=True,         # wait for dialogue to finish each tick
            dialogue_max_turns=3,
            agent_step_size=1.2,            # how far an agent moves per tick
            random_walk_step=0.1,           # small random jitter in movement
            missions_enabled=True,          # agents receive "visit X" goals
            mission_duration_ticks=10,
            seed=99,                        # reproducible run
        ),
        llm_provider="mock",                # change to "ollama" or "openrouter"
        enable_missions=True,
        enable_dialogue=True,
    )


# ── Step 3: Build and run ────────────────────────────────────────────────────

TICKS = 15


def main() -> None:
    scenario = build_party_scenario()
    engine = scenario.build_engine()

    # Spread agents in a circle near the center of the world
    agents = scenario.agent_names
    for idx, state in enumerate(engine._agents.values()):  # type: ignore[attr-defined]
        angle = (2 * math.pi * idx) / len(agents)
        state.position = (
            7.5 + 2.0 * math.cos(angle),
            7.5 + 2.0 * math.sin(angle),
        )

    print(f"=== custom_scenario: {scenario.name} ===")
    print(f"  Agents : {scenario.agent_names}")
    print(f"  POIs   : {[p.name for p in scenario.world.pois]}")
    print(f"  Ticks  : {TICKS}\n")

    for tick_num in range(1, TICKS + 1):
        result = engine.advance()
        for event in result.events:
            if event.get("type") == "interaction":
                names = " & ".join(event.get("agent_names", []))
                print(f"  tick {tick_num:2d}  {names} met")
            elif event.get("type") == "mission_complete":
                print(f"  tick {tick_num:2d}  {event.get('agent_name')} completed: {event.get('mission')}")

    stats = engine.stats()
    print("\n--- Final stats ---")
    print(f"  Interactions     : {stats['interactions']}")
    print(f"  Dialogues        : {stats['dialogues']}")
    print(f"  Missions done    : {stats.get('missions_completed', 0)}")

    # ── Bonus: alternative using Scenario.from_profile() ─────────────────────
    # If you have a LaunchProfile preset, you can avoid manual wiring:
    #
    #   from config.launch_profile import load_profile
    #   from config.scenario import Scenario
    #   scenario = Scenario.from_profile(load_profile("fast"))
    #   engine = scenario.build_engine()
    #
    # See config/launch_profile.py for available presets:
    #   "fast", "blocking_balanced", "dense_100", "complex", "long"

    print("\nTip: edit build_party_world() and build_party_scenario() to create")
    print("     your own scenario. Change llm_provider='ollama' for real dialogues.")


if __name__ == "__main__":
    main()
