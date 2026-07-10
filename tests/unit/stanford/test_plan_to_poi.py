"""Tests for Stanford plan-to-POI matching."""
from __future__ import annotations

import pytest

from gen_agent.integrations.stanford.plan_to_poi import (
    apply_plan_to_agent,
    extract_concrete_goals,
    match_goal_to_poi,
    resolve_plan_to_poi,
    _fuzzy_match_ratio,
)


class MockWorld:
    def __init__(self, pois):
        self.pois = pois


class MockPOI:
    def __init__(self, name: str, tags: list = None):
        self.name = name
        self.id = name.lower().replace(" ", "_")
        self.tags = tags or []
        self.x = 0.0
        self.y = 0.0


class MockAgent:
    def __init__(self):
        self.target_poi = None
        self.extra: dict = {}


class TestExtractGoals:
    def test_extracts_go_to_goals(self):
        plan = "1. Go to the library to read books. 2. Visit the cafe for coffee."
        goals = extract_concrete_goals(plan)
        assert len(goals) >= 1
        assert any("library" in g.lower() for g in goals)

    def test_extracts_visit_goals(self):
        plan = "Visit the park in the morning. Then go to the market."
        goals = extract_concrete_goals(plan)
        assert len(goals) >= 1

    def test_empty_plan(self):
        goals = extract_concrete_goals("")
        assert goals == []


class TestFuzzyMatch:
    def test_exact_match(self):
        ratio = _fuzzy_match_ratio("library", "library")
        assert ratio >= 0.9

    def test_partial_match(self):
        ratio = _fuzzy_match_ratio("public library", "library")
        assert ratio > 0.5

    def test_no_match(self):
        ratio = _fuzzy_match_ratio("hospital", "library")
        assert ratio < 0.5


class TestMatchGoalToPOI:
    def test_matches_library(self):
        pois = [MockPOI("Library"), MockPOI("Park"), MockPOI("Cafe")]
        goals = extract_concrete_goals("go to the library")
        assert goals, "extract_concrete_goals should find at least one goal"
        result = match_goal_to_poi(goals[0], pois)
        assert result is not None
        name = result.get("name", "") if isinstance(result, dict) else getattr(result, "name", "")
        assert "library" in name.lower() or "library" in goals[0]

    def test_returns_none_no_match(self):
        pois = [MockPOI("Library"), MockPOI("Park")]
        poi = match_goal_to_poi("hospital", pois)
        # threshold=0.4 so hospital should not match library or park
        assert poi is None

    def test_empty_poi_list(self):
        poi = match_goal_to_poi("library", [])
        assert poi is None


class TestResolveAndApply:
    def test_coffee_alias_matches_cafe(self):
        pois = [MockPOI("Cafe"), MockPOI("Park")]
        result = match_goal_to_poi("coffee", pois)
        assert result is not None
        assert "cafe" in str(result.get("name", "")).lower()

    def test_fallback_assigns_poi_when_no_strict_match(self):
        pois = [MockPOI("Library"), MockPOI("Park")]
        world = MockWorld(pois)
        agent = MockAgent()
        matched = apply_plan_to_agent(
            agent, "chat with a friend about the weather", world, allow_fallback=True
        )
        assert matched is not None
        assert agent.target_poi is not None
        assert agent.extra.get("concrete_goal_poi", {}).get("source") == "plan"

    def test_no_fallback_when_disabled(self):
        pois = [MockPOI("Library"), MockPOI("Park")]
        world = MockWorld(pois)
        agent = MockAgent()
        matched = apply_plan_to_agent(
            agent, "chat with a friend", world, allow_fallback=False
        )
        assert matched is None
