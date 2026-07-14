"""Unit tests for SimEngine."""
import math

import pytest

from gen_agent.agents.emotions import EmotionState
from gen_agent.interfaces.sim_protocol import AgentConfig
from gen_agent.sim.engine import SimConfig, SimEngine


def _make_engine(radius: float = 5.0, gap: int = 1, **kwargs) -> SimEngine:
    return SimEngine(SimConfig(interaction_radius=radius, min_gap_ticks=gap, **kwargs))


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


# ---------------------------------------------------------------------------
# Snapshot / state queries
# ---------------------------------------------------------------------------

def test_snapshot_contains_tick_and_agents():
    engine = _make_engine()
    engine.register_agent(AgentConfig("a1", "Alice", (0.0, 0.0)))
    engine.advance()
    snap = engine.snapshot()
    assert snap["tick"] == 1
    assert "a1" in snap["agents"]


def test_stats_returns_dict_with_required_keys():
    engine = _make_engine()
    stats = engine.stats()
    for key in ("interactions", "dialogues", "missions_completed", "plan_to_poi_matches"):
        assert key in stats


def test_advance_empty_engine_no_events():
    engine = _make_engine()
    result = engine.advance()
    assert result.events == []
    assert result.tick == 1


# ---------------------------------------------------------------------------
# Movement / position
# ---------------------------------------------------------------------------

def test_agent_moves_toward_position_each_tick():
    """Agent with a fixed random walk step changes position over ticks."""
    engine = SimEngine(SimConfig(random_walk_step=1.0, seed=0))
    engine.register_agent(AgentConfig("a1", "Alice", (10.0, 10.0)))
    pos_before = engine._agents["a1"].position
    engine.advance()
    pos_after = engine._agents["a1"].position
    dist = math.hypot(pos_after[0] - pos_before[0], pos_after[1] - pos_before[1])
    assert dist > 0  # moved at least a little


# ---------------------------------------------------------------------------
# Emotion contagion
# ---------------------------------------------------------------------------

def test_emotion_contagion_pulls_toward_neighbor():
    """Two nearby agents should have emotions influenced by each other."""
    engine = _make_engine(radius=10.0)
    engine.register_agent(AgentConfig("a1", "Alice", (0.0, 0.0)))
    engine.register_agent(AgentConfig("a2", "Bob", (1.0, 0.0)))
    # Force distinct valences
    engine._agents["a1"].emotions = EmotionState(valence=1.0, arousal=0.5, stress=0.0)
    engine._agents["a2"].emotions = EmotionState(valence=-1.0, arousal=0.5, stress=0.0)
    engine.advance()
    # After contagion a1 valence should be pulled down slightly (< 1.0)
    assert engine._agents["a1"].emotions.valence < 1.0


# ---------------------------------------------------------------------------
# NEAT API surface
# ---------------------------------------------------------------------------

def test_set_and_disable_neat_policy():
    engine = _make_engine()
    engine.register_agent(AgentConfig("a1", "Alice", (0.0, 0.0)))

    class DummyPolicy:
        def act(self, obs):
            return None

    engine.set_neat_policy_for_all(lambda s: DummyPolicy())
    assert engine._agents["a1"].neat_enabled

    engine.disable_neat_for_all()
    assert not engine._agents["a1"].neat_enabled
    assert engine._agents["a1"].neat_policy is None


def test_set_neat_policy_for_single_agent():
    engine = _make_engine()
    engine.register_agent(AgentConfig("a1", "Alice"))
    engine.register_agent(AgentConfig("a2", "Bob"))

    class DummyPolicy:
        def act(self, obs):
            return None

    engine.set_neat_policy_for_agent("a1", DummyPolicy())
    assert engine._agents["a1"].neat_enabled
    assert not engine._agents["a2"].neat_enabled


# ---------------------------------------------------------------------------
# Multiple ticks / interaction count
# ---------------------------------------------------------------------------

def test_interaction_counter_increments():
    engine = _make_engine(radius=5.0, gap=1)
    engine.register_agent(AgentConfig("a1", "Alice", (0.0, 0.0)))
    engine.register_agent(AgentConfig("a2", "Bob", (1.0, 0.0)))
    engine.advance()  # tick 1 — interaction fires
    engine.advance()  # tick 2 — gap=1 so fires again
    stats = engine.stats()
    assert stats["interactions"] >= 2


def test_note_plan_poi_no_match_still_extracts_goals():
    engine = _make_engine()
    engine.note_plan_poi("walk to the library", matched=None)
    stats = engine.stats()
    assert stats["plan_goals_extracted"] >= 1
    assert stats["plan_to_poi_matches"] == 0


# ---------------------------------------------------------------------------
# Config properties
# ---------------------------------------------------------------------------

def test_config_property_returns_simconfig():
    cfg = SimConfig(seed=99)
    engine = SimEngine(cfg)
    assert engine.config is cfg


def test_agents_property_returns_list():
    engine = _make_engine()
    engine.register_agent(AgentConfig("a1", "Alice"))
    engine.register_agent(AgentConfig("a2", "Bob"))
    assert len(engine.agents) == 2


def test_world_property_none_by_default():
    engine = _make_engine()
    assert engine.world is None
