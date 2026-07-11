"""
Dialogue quality scoring — prevents repetitive, empty, or degenerate responses.

score_utterance() returns a float in [0, 1].
DialogueEngine uses it to retry generation when score < threshold.
"""
from __future__ import annotations

import re

_MIN_WORDS = 5
_STUB_MARKERS = ("[stub]", "[llm", "[ollama", "[openrouter", "[council", "[error")


def score_utterance(text: str, history: list[str]) -> float:
    """
    Composite quality score for a single utterance.

    Penalises:
      - too short (< _MIN_WORDS words)
      - is a stub/error placeholder
      - high word overlap with recent history (repetition)
    """
    if not text or not text.strip():
        return 0.0

    lower = text.lower().strip()

    # Reject stub/error markers
    if any(lower.startswith(m) for m in _STUB_MARKERS):
        return 0.1

    words = _tokenise(lower)
    if len(words) < _MIN_WORDS:
        return 0.2

    # Repetition penalty: overlap with last 3 utterances
    rep_score = 1.0
    if history:
        recent_words = _tokenise(" ".join(history[-3:]).lower())
        if recent_words:
            overlap = len(set(words) & set(recent_words)) / max(len(set(words)), 1)
            rep_score = max(0.0, 1.0 - overlap * 0.8)

    # Length bonus (up to 40 words is good, beyond is fine)
    length_score = min(1.0, len(words) / 20)

    return round((rep_score * 0.7 + length_score * 0.3), 3)


def _tokenise(text: str) -> list[str]:
    return [w for w in re.split(r"\W+", text) if len(w) > 2]
