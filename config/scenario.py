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
        """
        Build and return a fully configured SimEngine.

        Wires together: LLM provider, memory manager, mission system,
        dialogue engine, and registers all agents.
        """
        from gen_agent.dialogue.dialogue_engine import DialogueEngine
        from gen_agent.llm.provider import get_llm_provider
        from gen_agent.memory.manager import MemoryManager
        from gen_agent.sim.missions import MissionSystem
        from gen_agent.interfaces.sim_protocol import AgentConfig
        import random
        import uuid

        os.environ.setdefault("LLM_PROVIDER", self.llm_provider)
        llm_prov = get_llm_provider(self.llm_provider)
        memory = MemoryManager()
        dialogue = (
            DialogueEngine(
                llm=llm_prov.complete,
                memory_store=memory,
                max_turns=self.sim_config.dialogue_max_turns,
            )
            if self.enable_dialogue
            else None
        )
        missions = (
            MissionSystem(
                world=self.world,
                mission_duration_ticks=self.sim_config.mission_duration_ticks,
            )
            if self.enable_missions and self.world.pois
            else None
        )
        cfg = self.sim_config
        cfg.missions_enabled = self.enable_missions

        engine = SimEngine(
            config=cfg,
            dialogue_engine=dialogue,
            memory_store=memory,
            world=self.world,
            mission_system=missions,
        )

        rng = random.Random(cfg.seed)
        for name in self.agent_names:
            agent_id = str(uuid.uuid4())[:8]
            pos = self.world.random_position(rng) if self.world else (
                rng.uniform(0, 20), rng.uniform(0, 20)
            )
            engine.register_agent(AgentConfig(
                agent_id=agent_id,
                name=name,
                position=pos,
            ))

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
