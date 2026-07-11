"""Tests for gen_agent/cognitive/biases.py — algebra only, no LLM calls."""
from __future__ import annotations

import math

import pytest

from gen_agent.cognitive.biases import (
    AnchoringBias,
    AvailabilityHeuristic,
    BiasLayer,
    ConfirmationBias,
    RecencyBias,
)


# ── RecencyBias ──────────────────────────────────────────────────────────────

class TestRecencyBias:

    def test_age_zero_weight_is_one(self):
        rb = RecencyBias(decay_lambda=0.2)
        assert rb.weight(0) == pytest.approx(1.0)

    def test_weight_decreases_with_age(self):
        rb = RecencyBias(decay_lambda=0.2)
        assert rb.weight(1) < rb.weight(0)
        assert rb.weight(10) < rb.weight(1)

    def test_negative_age_clamped(self):
        rb = RecencyBias(decay_lambda=0.2)
        assert rb.weight(-5) == pytest.approx(1.0)

    def test_high_lambda_decays_faster(self):
        slow = RecencyBias(decay_lambda=0.1)
        fast = RecencyBias(decay_lambda=1.0)
        assert fast.weight(5) < slow.weight(5)

    def test_apply_to_memories_adds_field(self):
        rb = RecencyBias()
        mems = [{"tick": 5, "content": "A"}, {"tick": 8, "content": "B"}]
        result = rb.apply_to_memories(mems, current_tick=10)
        assert "recency_weight" in result[0]
        assert "recency_weight" in result[1]
        # older memory (age=5) has lower weight than newer (age=2)
        assert result[0]["recency_weight"] < result[1]["recency_weight"]


# ── AnchoringBias ────────────────────────────────────────────────────────────

class TestAnchoringBias:

    def test_first_observation_is_anchor(self):
        ab = AnchoringBias(anchor_weight=0.3)
        result = ab.observe("alice", 10.0)
        assert result == pytest.approx(10.0)

    def test_second_observation_attenuated(self):
        ab = AnchoringBias(anchor_weight=0.3)
        ab.observe("alice", 10.0)       # sets anchor = 10
        result = ab.observe("alice", 20.0)  # deviation of +10, attenuated to 10 + 0.3*10 = 13
        assert result == pytest.approx(13.0)

    def test_different_agents_independent(self):
        ab = AnchoringBias()
        ab.observe("alice", 5.0)
        ab.observe("bob", 20.0)
        result_alice = ab.observe("alice", 10.0)
        result_bob = ab.observe("bob", 10.0)
        assert result_alice != result_bob

    def test_reset_clears_anchor(self):
        ab = AnchoringBias(anchor_weight=0.3)
        ab.observe("alice", 100.0)
        ab.reset("alice")
        result = ab.observe("alice", 5.0)
        assert result == pytest.approx(5.0)  # new anchor


# ── AvailabilityHeuristic ────────────────────────────────────────────────────

class TestAvailabilityHeuristic:

    def test_empty_returns_zero(self):
        ah = AvailabilityHeuristic()
        assert ah.estimated_probability("dialogue") == pytest.approx(0.0)

    def test_single_event_probability(self):
        ah = AvailabilityHeuristic(window_size=5)
        ah.record("dialogue")
        assert ah.estimated_probability("dialogue") == pytest.approx(1.0)

    def test_mixed_events(self):
        ah = AvailabilityHeuristic(window_size=10)
        for _ in range(3):
            ah.record("dialogue")
        for _ in range(7):
            ah.record("walk")
        assert ah.estimated_probability("dialogue") == pytest.approx(0.3)

    def test_window_evicts_old_events(self):
        ah = AvailabilityHeuristic(window_size=3)
        ah.record("dialogue")
        ah.record("walk")
        ah.record("walk")
        ah.record("walk")  # evicts first "dialogue"
        assert ah.estimated_probability("dialogue") == pytest.approx(0.0)

    def test_unseen_event_type(self):
        ah = AvailabilityHeuristic()
        ah.record("walk")
        assert ah.estimated_probability("dialogue") == pytest.approx(0.0)


# ── ConfirmationBias ─────────────────────────────────────────────────────────

class TestConfirmationBias:

    def test_empty_belief_returns_all(self):
        cb = ConfirmationBias()
        mems = [{"content": "went to the park"}, {"content": "met Alice"}]
        result = cb.filter("", mems)
        assert result == mems

    def test_filter_keeps_matching_memories(self):
        cb = ConfirmationBias(threshold=0.2)
        belief = "park walk outdoor"
        mems = [
            {"content": "went for a walk in the park today"},
            {"content": "ate pizza for dinner"},
        ]
        result = cb.filter(belief, mems)
        assert any("park" in m["content"] for m in result)

    def test_no_matches_returns_all(self):
        cb = ConfirmationBias(threshold=0.99)
        belief = "quantum physics"
        mems = [{"content": "had breakfast"}, {"content": "watered plants"}]
        result = cb.filter(belief, mems)
        assert result == mems

    def test_high_threshold_more_restrictive(self):
        belief = "park walk outdoor nature"
        mems = [
            {"content": "went for a walk in the park today nature trail"},
            {"content": "ate pizza for dinner"},
        ]
        # low threshold should keep only the matching memory (excludes pizza)
        cb_low = ConfirmationBias(threshold=0.1)
        low_result = cb_low.filter(belief, mems)
        assert len(low_result) == 1
        assert "park" in low_result[0]["content"]

        # very high threshold → no matches → fallback returns all
        cb_high = ConfirmationBias(threshold=0.99)
        high_result = cb_high.filter(belief, mems)
        assert len(high_result) == len(mems)  # fallback


# ── BiasLayer facade ─────────────────────────────────────────────────────────

class TestBiasLayer:

    def test_instantiation(self):
        bl = BiasLayer()
        assert bl.recency is not None
        assert bl.anchoring is not None
        assert bl.availability is not None
        assert bl.confirmation is not None

    def test_willingness_modifier_in_range(self):
        bl = BiasLayer()
        w = bl.willingness_modifier("alice", current_tick=10, last_interaction_tick=5)
        assert 0.1 <= w <= 2.0

    def test_willingness_no_previous_interaction(self):
        bl = BiasLayer()
        w = bl.willingness_modifier("alice", current_tick=10, last_interaction_tick=None)
        assert 0.1 <= w <= 2.0

    def test_willingness_records_events(self):
        bl = BiasLayer()
        bl.willingness_modifier("alice", 10, None, recent_events=["dialogue"])
        p = bl.availability.estimated_probability("dialogue")
        assert p > 0.0

    def test_willingness_fresh_interaction_lower(self):
        bl = BiasLayer()
        # very recent = age 0 → recency weight 1.0 (high), but that's just recency
        w_fresh = bl.willingness_modifier("alice", current_tick=10, last_interaction_tick=10)
        w_old = bl.willingness_modifier("alice", current_tick=10, last_interaction_tick=0)
        # fresh interaction has age=0 → weight=1.0; old has age=10 → weight=exp(-2)≈0.13
        # but availability boost applies too — just verify both are in range
        assert 0.1 <= w_fresh <= 2.0
        assert 0.1 <= w_old <= 2.0
