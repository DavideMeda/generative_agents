"""Unit tests for SimEngine."""
import pytest

from gen_agent.interfaces.sim_protocol import AgentConfig
from gen_agent.sim.engine import SimConfig, SimEngine


def _make_engine(radius: float = 5.0, gap: int = 1) -> SimEngine:
    return SimEngine(SimConfig(interaction_radius=radius, min_gap_ticks=gap))


def test_register_agent_returns_id():
    engine = _make_engine()
    aid = engine.register_agent(AgentConfig(agent_id="a1", name="Alice", position=(0.0, 0.0)))
    assert aid == "a1"


def test_advance_increments_tick():
    engine = _make_engine()
    result = engine.advance()
    assert result.tick == 1
    result2 = engine.advance()
    assert result2.tick == 2


def test_nearby_agents_interact():
    engine = _make_engine(radius=5.0, gap=1)
    engine.register_agent(AgentConfig("a1", "Alice", (0.0, 0.0)))
    engine.register_agent(AgentConfig("a2", "Bob", (1.0, 0.0)))  # within radius
    result = engine.advance()
    interaction_events = [e for e in result.events if e["type"] == "interaction"]
    assert len(interaction_events) == 1


def test_far_agents_do_not_interact():
    engine = _make_engine(radius=2.0)
    engine.register_agent(AgentConfig("a1", "Alice", (0.0, 0.0)))
    engine.register_agent(AgentConfig("a2", "Bob", (100.0, 0.0)))  # far away
    result = engine.advance()
    assert result.events == []


def test_cooldown_prevents_double_interaction():
    engine = _make_engine(radius=5.0, gap=5)
    engine.register_agent(AgentConfig("a1", "Alice", (0.0, 0.0)))
    engine.register_agent(AgentConfig("a2", "Bob", (1.0, 0.0)))
    engine.advance()  # tick 1 — interaction fires
    result2 = engine.advance()  # tick 2 — still in cooldown
    assert result2.events == []


def test_reset_clears_state():
    engine = _make_engine()
    engine.register_agent(AgentConfig("a1", "Alice"))
    engine.advance()
    engine.reset()
    snap = engine.snapshot()
    assert snap["tick"] == 0
    assert snap["agents"] == {}


def test_agent_limit_raises():
    engine = SimEngine(SimConfig(max_agents=2))
    engine.register_agent(AgentConfig("a1", "Alice"))
    engine.register_agent(AgentConfig("a2", "Bob"))
    with pytest.raises(RuntimeError, match="Agent limit"):
        engine.register_agent(AgentConfig("a3", "Carol"))


def test_note_plan_poi_increments_stats():
    engine = _make_engine()
    engine.note_plan_poi("go to the cafe and visit the park", "Cafe")
    stats = engine.stats()
    assert stats["plan_goals_extracted"] >= 1
    assert stats["plan_to_poi_matches"] == 1
    assert stats["plan_goals_matched_to_poi"] == 1
