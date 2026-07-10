"""Tests for dialogue_guards module."""
from __future__ import annotations

from gen_agent.dialogue.dialogue_guards import (
    clean_utterance,
    sanitize_memory_for_prompt,
    build_retry_hint,
    detect_italian,
)


def test_clean_utterance_strips_label():
    assert clean_utterance("Marco: Hello there, how are you?", "Marco") == "Hello there, how are you?"


def test_clean_utterance_strips_stage_direction():
    result = clean_utterance("(smiling) Hello there, nice to meet you today.", "Lucia")
    assert "smiling" not in result
    assert "Hello" in result


def test_sanitize_memory_passes_clean_content():
    content = "Walked to the park and met Lucia by the fountain."
    result = sanitize_memory_for_prompt(content)
    assert result == content.strip()[:200]


def test_sanitize_memory_filters_meta():
    content = "As an AI language model I cannot generate this."
    result = sanitize_memory_for_prompt(content)
    assert result == ""


def test_sanitize_memory_filters_italian():
    content = "Ciao Marco, come stai? Sono molto felice di vederti qui davvero."
    result = sanitize_memory_for_prompt(content)
    assert result == ""


def test_detect_italian_returns_true_for_italian():
    assert detect_italian("Ciao Marco, come stai? Sono felice di vederti qui.")


def test_detect_italian_returns_false_for_english():
    assert not detect_italian("Hello Marco, how are you today? I am happy to see you.")


def test_retry_hint_mentions_reason():
    hint = build_retry_hint("too short", "Lucia", "Marco", 25)
    assert len(hint) > 10
    assert "25" in hint or "word" in hint.lower()
