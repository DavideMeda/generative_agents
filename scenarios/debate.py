"""
Debate scenario — 3 agents with high interaction rate, longer dialogues.
Intended to test consensus and social learning modules.
"""
from config.scenario import Scenario
from gen_agent.sim.engine import SimConfig
from gen_agent.world.world import seed_default_world

SCENARIO = Scenario(
    name="debate",
    description="Three agents debating in a town hall setting (mock LLM).",
    agent_names=["Sophia", "Marcus", "Lena"],
    world=seed_default_world(),
    sim_config=SimConfig(
        tick_interval_sec=0.0,
        interaction_radius=5.0,    # large radius — they always find each other
        min_gap_ticks=3,
        block_on_dialogue=True,
        dialogue_max_turns=8,
        agent_step_size=1.5,
        missions_enabled=False,    # pure debate, no wandering goals
        seed=7,
    ),
    llm_provider="mock",
    enable_missions=False,
    enable_dialogue=True,
)
