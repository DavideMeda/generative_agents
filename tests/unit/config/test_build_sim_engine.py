"""
Tests for build_sim_engine and Scenario.

These use mock LLM (no network) and SQLite (:memory:) to stay fast and offline.
They cover engine_factory.py which was previously at 0% coverage.
"""
from __future__ import annotations

import pytest

from config.scenario import Scenario, load_scenario
from gen_agent.sim.engine import SimConfig, SimEngine

# ---------------------------------------------------------------------------
# Minimal scenario fixture
# ---------------------------------------------------------------------------

def _minimal_scenario(**overrides) -> Scenario:
    """3-agent mock scenario — fast and offline."""
    defaults = dict(
        name="test",
        description="unit test",
        agent_names=["Alice", "Bob", "Carol"],
        llm_provider="mock",
        enable_missions=False,
        enable_dialogue=True,
    )
    defaults.update(overrides)
    return Scenario(**defaults)


# ---------------------------------------------------------------------------
# build_sim_engine — basic wiring
# ---------------------------------------------------------------------------

class TestBuildSimEngine:
    def test_returns_sim_engine(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEN_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ENABLE_STANFORD_WORKER", "false")
        scenario = _minimal_scenario()
        engine = scenario.build_engine()
        assert isinstance(engine, SimEngine)

    def test_agents_registered(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEN_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ENABLE_STANFORD_WORKER", "false")
        scenario = _minimal_scenario()
        engine = scenario.build_engine()
        assert len(engine._agents) == 3

    def test_agent_names_match(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEN_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ENABLE_STANFORD_WORKER", "false")
        scenario = _minimal_scenario()
        engine = scenario.build_engine()
        names = {a.name for a in engine._agents.values()}
        assert names == {"Alice", "Bob", "Carol"}

    def test_engine_can_advance(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEN_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ENABLE_STANFORD_WORKER", "false")
        scenario = _minimal_scenario(
            sim_config=SimConfig(tick_interval_sec=0.0, interaction_radius=50.0, seed=42),
        )
        engine = scenario.build_engine()
        result = engine.advance()
        assert result.tick == 1

    def test_stats_returns_dict(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEN_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ENABLE_STANFORD_WORKER", "false")
        scenario = _minimal_scenario()
        engine = scenario.build_engine()
        stats = engine.stats()
        assert isinstance(stats, dict)
        assert "dialogues" in stats

    def test_no_dialogue_engine_when_disabled(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEN_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ENABLE_STANFORD_WORKER", "false")
        scenario = _minimal_scenario(enable_dialogue=False)
        engine = scenario.build_engine()
        assert engine._dialogue is None

    def test_circuit_breaker_not_applied_to_mock(self, tmp_path, monkeypatch):
        """CircuitBreaker must never wrap mock provider (no network, no need)."""
        monkeypatch.setenv("GEN_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ENABLE_STANFORD_WORKER", "false")
        monkeypatch.setenv("ENABLE_CIRCUIT_BREAKER", "true")
        scenario = _minimal_scenario(llm_provider="mock")
        # Should not raise — mock bypasses circuit breaker
        engine = scenario.build_engine()
        assert isinstance(engine, SimEngine)


# ---------------------------------------------------------------------------
# Scenario.from_profile
# ---------------------------------------------------------------------------

class TestScenarioFromProfile:
    def test_from_fast_profile(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEN_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ENABLE_STANFORD_WORKER", "false")
        from config.launch_profile import load_profile
        profile = load_profile("fast")
        scenario = Scenario.from_profile(profile)
        assert scenario.name == "fast"
        assert len(scenario.agent_names) >= 1

    def test_from_profile_llm_provider(self):
        from config.launch_profile import load_profile
        profile = load_profile("fast")
        scenario = Scenario.from_profile(profile)
        assert scenario.llm_provider == profile.llm_provider


# ---------------------------------------------------------------------------
# load_scenario
# ---------------------------------------------------------------------------

class TestLoadScenario:
    def test_load_offline_scenario(self):
        scenario = load_scenario("offline")
        assert isinstance(scenario, Scenario)
        assert len(scenario.agent_names) >= 3

    def test_load_default_scenario(self):
        scenario = load_scenario("default")
        assert isinstance(scenario, Scenario)

    def test_unknown_scenario_raises(self):
        with pytest.raises(ValueError, match="not found"):
            load_scenario("__nonexistent_xyz__")

    def test_load_debate_scenario(self):
        scenario = load_scenario("debate")
        assert isinstance(scenario, Scenario)


# ---------------------------------------------------------------------------
# env flags — biases layer
# ---------------------------------------------------------------------------

class TestEnvFlags:
    def test_biases_enabled_injects_layer(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEN_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ENABLE_STANFORD_WORKER", "false")
        monkeypatch.setenv("ENABLE_BIASES", "true")
        scenario = _minimal_scenario()
        engine = scenario.build_engine()
        assert engine._biases is not None
        monkeypatch.delenv("ENABLE_BIASES")

    def test_biases_disabled_by_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEN_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ENABLE_STANFORD_WORKER", "false")
        monkeypatch.delenv("ENABLE_BIASES", raising=False)
        scenario = _minimal_scenario()
        engine = scenario.build_engine()
        assert engine._biases is None
