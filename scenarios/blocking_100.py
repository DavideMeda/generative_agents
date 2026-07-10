"""
Blocking 100-tick scenario — mirrors legacy blocking_balanced (Profile B)
but capped at 100 ticks. 5 agents, 8 POI, Ollama blocking dialogues.
"""
from config.scenario import Scenario
from gen_agent.sim.engine import SimConfig
from gen_agent.world.world import seed_default_world

SCENARIO = Scenario(
    name="blocking_100",
    description=(
        "5 agents, 100 ticks, blocking Ollama dialogues, "
        "blocking_balanced-like interaction params (radius=5, every=10, min_gap=32)."
    ),
    agent_names=["Marco", "Lucia", "Giovanni", "Anna", "Elena"],
    world=seed_default_world(),
    sim_config=SimConfig(
        tick_interval_sec=0.0,
        interaction_radius=5.0,
        min_gap_ticks=32,
        interaction_every_ticks=10,
        block_on_dialogue=True,
        dialogue_max_turns=3,
        dialogue_wait_timeout_seconds=180.0,
        agent_step_size=0.8,
        random_walk_step=0.0,
        missions_enabled=True,
        mission_duration_ticks=30,
        seed=42,
    ),
    llm_provider="ollama",
    enable_missions=True,
    enable_dialogue=True,
)
