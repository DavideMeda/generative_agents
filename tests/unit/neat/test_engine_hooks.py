"""Tests for NEAT hooks on SimEngine."""
from __future__ import annotations

import pytest

from gen_agent.sim.engine import SimConfig, SimEngine
from gen_agent.interfaces.sim_protocol import AgentConfig


def _make_engine(seed: int = 42) -> SimEngine:
    cfg = SimConfig(
        interaction_radius=10.0,
        min_gap_ticks=1,
        block_on_dialogue=False,
        seed=seed,
    )
    return SimEngine(config=cfg)


class MockPolicy:
    """Minimal NEAT policy stub."""
    def __init__(self):
        self.call_count = 0

    def act(self, observation):
        self.call_count += 1
        return [0.1, 0.1]  # dx, dy


class TestNeatEngineHooks:
    def test_set_neat_policy_for_all(self):
        engine = _make_engine()
        engine.register_agent(AgentConfig("a1", "Marco", (0.0, 0.0)))
        engine.register_agent(AgentConfig("a2", "Lucia", (1.0, 0.0)))

        policy = MockPolicy()
        engine.set_neat_policy_for_all(lambda _: policy, mode="movement")

        for s in engine.agents:
            assert s.neat_enabled
            assert s.neat_mode == "movement"

    def test_disable_neat_for_all(self):
        engine = _make_engine()
        engine.register_agent(AgentConfig("a1", "Marco", (0.0, 0.0)))

        policy = MockPolicy()
        engine.set_neat_policy_for_all(lambda _: policy)
        engine.disable_neat_for_all()

        for s in engine.agents:
            assert not s.neat_enabled
            assert s.neat_policy is None

    def test_neat_policy_called_on_advance(self):
        engine = _make_engine()
        engine.register_agent(AgentConfig("a1", "Marco", (0.0, 0.0)))

        policy = MockPolicy()
        engine.set_neat_policy_for_all(lambda _: policy, mode="movement")
        engine.advance()

        assert policy.call_count >= 1

    def test_set_neat_policy_for_single_agent(self):
        engine = _make_engine()
        engine.register_agent(AgentConfig("a1", "Marco", (0.0, 0.0)))
        engine.register_agent(AgentConfig("a2", "Lucia", (1.0, 0.0)))

        policy = MockPolicy()
        engine.set_neat_policy_for_agent("a1", policy, mode="movement")

        states = {s.agent_id: s for s in engine.agents}
        assert states["a1"].neat_enabled
        assert not states["a2"].neat_enabled

    def test_neat_snapshot_includes_neat_field(self):
        engine = _make_engine()
        engine.register_agent(AgentConfig("a1", "Marco", (0.0, 0.0)))

        policy = MockPolicy()
        engine.set_neat_policy_for_all(lambda _: policy)
        engine.advance()

        snap = engine.snapshot()
        for aid, data in snap["agents"].items():
            assert "neat" in data
