"""
Offline scenario — same world as default, but uses mock LLM.
No network connection required. Ideal for CI and local testing.
"""
from config.scenario import Scenario
from gen_agent.sim.engine import SimConfig
from gen_agent.world.world import seed_default_world

SCENARIO = Scenario(
    name="offline",
    description="Five agents in a small town using mock LLM (no network).",
    agent_names=["Alice", "Bob", "Carol", "David", "Eve"],
    world=seed_default_world(),
    sim_config=SimConfig(
        tick_interval_sec=0.0,
        interaction_radius=2.5,
        min_gap_ticks=5,
        block_on_dialogue=True,
        dialogue_max_turns=4,
        agent_step_size=0.8,
        missions_enabled=True,
        mission_duration_ticks=30,
        seed=42,
    ),
    llm_provider="mock",
    enable_missions=True,
    enable_dialogue=True,
)
