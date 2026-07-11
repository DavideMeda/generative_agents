"""Tests for gen_agent/agents/traits.py (Big Five personality helpers)."""
from __future__ import annotations

import random

import pytest

from gen_agent.agents.traits import (
    BIG_FIVE,
    interaction_willingness,
    normalize,
    random_traits,
)


class TestNormalize:

    def test_all_keys_present(self):
        result = normalize({})
        assert set(result.keys()) == set(BIG_FIVE)

    def test_defaults_to_0_5(self):
        result = normalize({})
        for v in result.values():
            assert v == 0.5

    def test_clamps_above_1(self):
        result = normalize({"openness": 2.0})
        assert result["openness"] == 1.0

    def test_clamps_below_0(self):
        result = normalize({"neuroticism": -0.5})
        assert result["neuroticism"] == 0.0

    def test_passthrough_valid(self):
        traits = {k: 0.7 for k in BIG_FIVE}
        result = normalize(traits)
        for v in result.values():
            assert v == pytest.approx(0.7)

    def test_alias_open(self):
        # "open" is an alias for "openness" — check it resolves
        result = normalize({"openness": 0.9})
        assert result["openness"] == pytest.approx(0.9)


class TestRandomTraits:

    def test_returns_all_big_five_keys(self):
        t = random_traits()
        assert set(t.keys()) == set(BIG_FIVE)

    def test_values_are_floats(self):
        t = random_traits()
        for v in t.values():
            assert isinstance(v, float)

    def test_seeded_rng_reproducible(self):
        rng = random.Random(42)
        t1 = random_traits(rng=rng)
        rng2 = random.Random(42)
        t2 = random_traits(rng=rng2)
        assert t1 == t2

    def test_different_seeds_differ(self):
        t1 = random_traits(random.Random(1))
        t2 = random_traits(random.Random(999))
        assert t1 != t2


class TestInteractionWillingness:

    def test_high_extraversion_agreeableness(self):
        t = normalize({"extraversion": 1.0, "agreeableness": 1.0})
        w = interaction_willingness(t)
        assert w == pytest.approx(1.0)

    def test_low_extraversion_agreeableness(self):
        t = normalize({"extraversion": 0.0, "agreeableness": 0.0})
        w = interaction_willingness(t)
        assert w == pytest.approx(0.0)

    def test_midpoint(self):
        t = normalize({})  # all 0.5
        w = interaction_willingness(t)
        assert w == pytest.approx(0.5)

    def test_extraversion_weighted_more(self):
        # extraversion weight 0.6 > agreeableness weight 0.4
        t_high_e = normalize({"extraversion": 1.0, "agreeableness": 0.0})
        t_high_a = normalize({"extraversion": 0.0, "agreeableness": 1.0})
        assert interaction_willingness(t_high_e) > interaction_willingness(t_high_a)
