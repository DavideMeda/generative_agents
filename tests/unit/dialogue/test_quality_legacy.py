"""Tests for dialogue quality scoring and guards — ported from legacy."""
from __future__ import annotations

import pytest

from gen_agent.dialogue.dialogue_guards import validate_utterance, detect_meta, build_retry_hint
from gen_agent.dialogue.quality_legacy import score_utterance_legacy
from gen_agent.dialogue.intent_pack import build_intent_pack, intent_pack_to_prompt_section


class TestValidateUtterance:
    def test_valid_english(self):
        text = "Hey Marco, good to see you here at the park. How's your day going?"
        ok, reason = validate_utterance(text, "Lucia", "Marco", min_words=8)
        assert ok, reason

    def test_too_short(self):
        text = "Hi."
        ok, reason = validate_utterance(text, "Lucia", "Marco", min_words=8)
        assert not ok
        assert "short" in reason.lower() or "word" in reason.lower()

    def test_meta_reference(self):
        text = "As an AI language model I cannot generate dialogue about this simulation."
        ok, reason = validate_utterance(text, "Lucia", "Marco", min_words=8)
        assert not ok

    def test_italian_contamination(self):
        text = "Ciao Marco, come stai? Sono molto felice di vederti qui."
        ok, reason = validate_utterance(text, "Lucia", "Marco", min_words=8)
        assert not ok

    def test_wrong_addressee(self):
        text = "Hey Anna, how are you today?"
        ok, reason = validate_utterance(
            text, "Lucia", "Marco", min_words=5,
            known_names=["Marco", "Lucia", "Anna", "Giovanni"]
        )
        assert not ok
        assert "address" in reason.lower() or "name" in reason.lower()

    def test_no_wrong_addressee_if_not_in_known_names(self):
        text = "Hey there, how are you today?"
        ok, reason = validate_utterance(text, "Lucia", "Marco", min_words=5)
        assert ok


class TestScoreUtteranceLegacy:
    def test_good_utterance_scores_above_threshold(self):
        text = (
            "Marco, I was thinking about what you said last week at the library. "
            "The new exhibition sounds fascinating — I'd love to go check it out with you."
        )
        score = score_utterance_legacy(text, [], "Lucia", "Marco")
        assert score >= 0.3

    def test_empty_scores_low(self):
        score = score_utterance_legacy("", [], "Lucia", "Marco")
        assert score <= 0.2

    def test_boilerplate_scores_low(self):
        text = "I agree completely. Yes indeed. Absolutely. I agree with what you said."
        score = score_utterance_legacy(text, [], "Lucia", "Marco")
        assert score < 0.6


class TestDetectMeta:
    def test_detects_simulation(self):
        assert detect_meta("This is a simulation of reality.")

    def test_detects_ai_reference(self):
        assert detect_meta("As an AI I cannot do this.")

    def test_clean_text_no_meta(self):
        assert not detect_meta("I went to the market this morning.")


class TestIntentPack:
    def test_cooperative_high_agreeableness(self):
        traits = {"openness": 0.5, "conscientiousness": 0.5,
                  "extraversion": 0.5, "agreeableness": 0.8, "neuroticism": 0.2}
        pack = build_intent_pack(traits, None, None, None)
        assert pack["stance"] in ("cooperative", "analytical", "energetic")

    def test_competitive_low_trust(self):
        traits = {"openness": 0.4, "conscientiousness": 0.5,
                  "extraversion": 0.4, "agreeableness": 0.2, "neuroticism": 0.7}
        rels = {"trust": 0.1, "valence": -0.5}
        pack = build_intent_pack(traits, None, rels, None)
        assert pack["stance"] in ("competitive", "provocative", "defensive")

    def test_prompt_section_contains_goal(self):
        traits = {"openness": 0.5, "conscientiousness": 0.5,
                  "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5}
        pack = build_intent_pack(traits, None, None, None)
        section = intent_pack_to_prompt_section(pack, "Marco")
        assert "Goal:" in section
        assert len(section) > 20
