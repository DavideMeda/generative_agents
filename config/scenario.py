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
"""
from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from typing import List, Optional

from gen_agent.sim.engine import SimConfig, SimEngine
from gen_agent.world.world import World, seed_default_world


@dataclass
class Scenario:
    name: str
    description: str
    agent_names: List[str]
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


def _list_scenarios() -> List[str]:
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent / "scenarios"
    return [p.stem for p in root.glob("*.py") if not p.stem.startswith("_")]
