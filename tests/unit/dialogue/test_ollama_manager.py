"""Tests for gen_agent/dialogue/ollama_manager.py — no real Ollama calls."""
from __future__ import annotations

import pytest

from gen_agent.dialogue.ollama_manager import (
    build_ollama_prompt,
    clean_dialogue_output,
    is_output_valid,
)


class TestCleanDialogueOutput:

    def test_strips_speaker_label(self):
        raw = "Alice: Hello there, how are you doing today?"
        result = clean_dialogue_output(raw)
        assert not result.startswith("Alice:")

    def test_strips_stage_directions_parens(self):
        raw = "Hey (smiling broadly) what's up?"
        result = clean_dialogue_output(raw)
        assert "(" not in result

    def test_strips_stage_directions_asterisks(self):
        raw = "Hey *nodding slowly* let's go."
        result = clean_dialogue_output(raw)
        assert "*" not in result

    def test_collapses_whitespace(self):
        raw = "Hello   there   friend"
        result = clean_dialogue_output(raw)
        assert "  " not in result

    def test_empty_string(self):
        assert clean_dialogue_output("") == ""

    def test_preserves_content(self):
        raw = "I really enjoyed that walk yesterday, didn't you?"
        result = clean_dialogue_output(raw)
        assert "walk" in result


class TestIsOutputValid:

    def test_valid_english(self):
        text = "The weather has been lovely lately, don't you think so too?"
        assert is_output_valid(text, min_words=5) is True

    def test_too_short(self):
        assert is_output_valid("hi", min_words=10) is False

    def test_meta_ai_reference_rejected(self):
        text = " ".join(["word"] * 15) + " as an AI language model I cannot"
        assert is_output_valid(text) is False

    def test_italian_contamination_rejected(self):
        text = "ciao come stai oggi, molto bene grazie, sono felice di vederti"
        assert is_output_valid(text, min_words=5) is False

    def test_single_italian_word_allowed(self):
        text = "I said 'ciao' to greet her, that was nice and natural I think"
        assert is_output_valid(text, min_words=5) is True

    def test_simulation_keyword_rejected(self):
        text = " ".join(["word"] * 15) + " this is a simulation environment"
        assert is_output_valid(text) is False


class TestBuildOllamaPrompt:

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            speaker_name="Alice",
            listener_name="Bob",
            memory_snippets=["saw Bob at the park"],
            location="Town Square",
            history="",
            scenario="A quiet afternoon in a small town.",
            min_words=20,
        )
        kwargs.update(overrides)
        return kwargs

    def test_returns_string(self):
        p = build_ollama_prompt(**self._base_kwargs())
        assert isinstance(p, str)

    def test_contains_speaker_name(self):
        p = build_ollama_prompt(**self._base_kwargs())
        assert "Alice" in p

    def test_contains_listener_name(self):
        p = build_ollama_prompt(**self._base_kwargs())
        assert "Bob" in p

    def test_contains_location(self):
        p = build_ollama_prompt(**self._base_kwargs())
        assert "Town Square" in p

    def test_no_memory_snippets(self):
        p = build_ollama_prompt(**self._base_kwargs(memory_snippets=[]))
        assert "none" in p

    def test_traits_section_included(self):
        traits = {"extraversion": 0.9, "openness": 0.5, "conscientiousness": 0.5,
                  "agreeableness": 0.5, "neuroticism": 0.5}
        p = build_ollama_prompt(**self._base_kwargs(traits=traits))
        assert "extraversion" in p

    def test_emotion_good_mood(self):
        emotions = {"valence": 0.5}
        p = build_ollama_prompt(**self._base_kwargs(emotions=emotions))
        assert "good mood" in p

    def test_emotion_tense(self):
        emotions = {"valence": -0.5}
        p = build_ollama_prompt(**self._base_kwargs(emotions=emotions))
        assert "tense" in p

    def test_min_words_appears_in_prompt(self):
        p = build_ollama_prompt(**self._base_kwargs(min_words=42))
        assert "42" in p
