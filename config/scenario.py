"""
Scenario loader and dataclass.

A Scenario bundles all configuration needed to spin up a simulation:
  - agent names
  - world layout
  - sim config
  - LLM provider name

Usage:
    scenario = load_scenario("default")
    engine = scenario.build_engine()

    # Or build from a LaunchProfile preset:
    from config.launch_profile import load_profile
    scenario = Scenario.from_profile(load_profile("fast"))
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from gen_agent.sim.engine import SimConfig, SimEngine
from gen_agent.world.world import World, seed_default_world

if TYPE_CHECKING:
    from config.launch_profile import LaunchProfile


@dataclass
class Scenario:
    name: str
    description: str
    agent_names: list[str]
    world: World = field(default_factory=seed_default_world)
    sim_config: SimConfig = field(default_factory=SimConfig)
    llm_provider: str = "mock"
    enable_missions: bool = True
    enable_dialogue: bool = True

    def build_engine(self) -> SimEngine:
        """Build fully wired SimEngine via central factory."""
        from config.engine_factory import build_sim_engine
        engine, _extras = build_sim_engine(self)
        return engine

    @classmethod
    def from_profile(cls, profile: LaunchProfile) -> Scenario:
        """Build a Scenario from a LaunchProfile preset (no manual bridging needed)."""
        return cls(
            name=profile.preset,
            description=profile.scenario_description,
            agent_names=profile.agent_names,
            world=seed_default_world(),
            sim_config=SimConfig(
                block_on_dialogue=profile.block_on_dialogue,
                dialogue_max_turns=profile.dialogue_max_turns,
                interaction_radius=profile.interaction_radius,
                min_gap_ticks=profile.min_gap_ticks,
                mission_duration_ticks=profile.mission_duration_ticks,
                seed=42,
            ),
            llm_provider=profile.llm_provider,
            enable_missions=True,
            enable_dialogue=True,
        )


def load_scenario(name: str) -> Scenario:
    """
    Load a scenario by name from the scenarios/ package.

    Raises ValueError if the scenario is not found.
    """
    try:
        module = importlib.import_module(f"scenarios.{name}")
    except ModuleNotFoundError:
        available = _list_scenarios()
        raise ValueError(
            f"Scenario '{name}' not found. Available: {available}"
        ) from None
    if not hasattr(module, "SCENARIO"):
        raise ValueError(f"scenarios/{name}.py must define a SCENARIO variable")
    return module.SCENARIO


def _list_scenarios() -> list[str]:
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent / "scenarios"
    return [p.stem for p in root.glob("*.py") if not p.stem.startswith("_")]
