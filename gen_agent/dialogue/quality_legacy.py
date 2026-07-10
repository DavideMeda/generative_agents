"""Legacy dialogue quality — CORE-light + ConsenSagent-style scoring (English only)."""
from __future__ import annotations

import json
import os
import re
import string
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from gen_agent.dialogue.dialogue_guards import validate_utterance

CORE_LEXICAL_WEIGHT = 0.7
CORE_PHRASE_WEIGHT = 0.3

def _float_env(name: str, default: float) -> float:
    try:
        v = os.environ.get(name)
        if v is not None:
            return float(v)
    except (TypeError, ValueError):
        pass
    return default

CORE_REGENERATE_THRESHOLD = _float_env("GEN_AGENT_CORE_REGENERATE_THRESHOLD", 0.6)
SYCOPHANCY_REGENERATE_THRESHOLD = _float_env("GEN_AGENT_SYCOPHANCY_REGENERATE_THRESHOLD", 0.35)
DIALOGUE_MIN_WORDS = int(os.getenv("DIALOGUE_MIN_WORDS", "25"))

ENGLISH_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "may", "might", "must", "i", "you", "he",
    "she", "it", "we", "they", "me", "him", "her", "us", "them", "my", "your", "his",
    "its", "our", "their", "this", "that", "these", "those", "what", "which", "who",
    "when", "where", "why", "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "no", "not", "only", "own", "same", "so", "than", "too",
    "very", "just", "also", "well", "like", "about", "into", "through", "during", "before",
    "after", "above", "below", "up", "down", "out", "off", "over", "under", "again",
})

TEMPLATE_PHRASES = [
    "the other time we saw",
    "if we move calmly",
    "when you helped me",
    "cooperation is fundamental",
    "communication is fundamental",
]

AGREEMENT_PHRASES = [
    "yes", "sure", "i agree", "exactly", "you're right", "absolutely", "right",
    "perfect", "correct", "indeed", "okay", "ok", "true", "fair point",
]
DISAGREEMENT_PHRASES = [
    "i'm not sure", "i don't think", "maybe not", "i have doubts", "i disagree",
    "i don't agree", "i doubt", "not really", "not exactly", "i oppose",
]


def _tokenize(text: str) -> List[str]:
    text = (text or "").lower().strip()
    for p in string.punctuation:
        text = text.replace(p, " ")
    return [w for w in text.split() if w]


def _filter_stopwords(words: List[str]) -> List[str]:
    return [w for w in words if w.lower() not in ENGLISH_STOP_WORDS]


def _get_bigrams(words: List[str]) -> List[tuple]:
    if len(words) < 2:
        return []
    return [(words[i], words[i + 1]) for i in range(len(words) - 1)]


def _get_trigrams(words: List[str]) -> List[tuple]:
    if len(words) < 3:
        return []
    return [(words[i], words[i + 1], words[i + 2]) for i in range(len(words) - 2)]


def _split_sentences(text: str) -> List[str]:
    if not (text or "").strip():
        return []
    parts = re.split(r"[.!?]+", text)
    return [p.strip().lower() for p in parts if p.strip()]


def _extract_turns(dialogue_text: str) -> List[str]:
    lines = [ln.strip() for ln in (dialogue_text or "").splitlines() if ln.strip()]
    turns: List[str] = []
    name_colon = re.compile(r"^([^:]+):\s*(.*)$", re.DOTALL)
    for line in lines:
        m = name_colon.match(line)
        if m:
            turn_text = m.group(2).strip()
            if turn_text:
                turns.append(turn_text)
        elif line:
            turns.append(line)
    return turns or ([dialogue_text.strip()] if dialogue_text else [])


def _jaccard_overlap(tokens_a: List[str], tokens_b: List[str]) -> float:
    sa, sb = set(tokens_a), set(tokens_b)
    if not sa and not sb:
        return 0.0
    union = len(sa | sb)
    return len(sa & sb) / union if union else 0.0


def compute_format_score(dialogue_text: str) -> Dict[str, Any]:
    turns = _extract_turns(dialogue_text)
    penalty = 0.0
    details: Dict[str, Any] = {"num_turns": len(turns), "issues": []}
    if not turns:
        return {"format_penalty": 1.0, "details": details}
    empty_turns = sum(1 for t in turns if not (t or "").strip())
    if empty_turns:
        penalty += 0.3 * min(1.0, empty_turns / max(1, len(turns)))
        details["issues"].append("empty_turns")
    return {"format_penalty": round(min(1.0, penalty), 4), "details": details}


def compute_core_score(
    dialogue_text: str,
    recent_utterances: Optional[List[str]] = None,
) -> Dict[str, Any]:
    words = _tokenize(dialogue_text)
    words_filtered = _filter_stopwords(words)
    bigrams = _get_bigrams(words_filtered)
    total_bigrams = len(bigrams)
    unique_bigrams = len(set(bigrams)) if bigrams else 0
    lexical_variety = unique_bigrams / max(1, total_bigrams)

    sentences = _split_sentences(dialogue_text)
    seen: Dict[str, int] = {}
    for s in sentences:
        key = re.sub(r"\s+", " ", s).strip()
        if key:
            seen[key] = seen.get(key, 0) + 1
    phrase_repetition_ratio = min(
        1.0,
        sum(c - 1 for c in seen.values() if c > 1) / max(1, len(sentences)),
    )

    dialogue_lower = (dialogue_text or "").lower()
    template_penalty = min(0.3, sum(1 for tp in TEMPLATE_PHRASES if tp in dialogue_lower) * 0.15)
    fmt = compute_format_score(dialogue_text)
    score = (
        CORE_LEXICAL_WEIGHT * lexical_variety
        + CORE_PHRASE_WEIGHT * (1.0 - phrase_repetition_ratio)
        - template_penalty
        - fmt["format_penalty"] * 0.1
    )
    return {
        "core_score": round(max(0.0, min(1.0, score)), 4),
        "lexical_variety": round(lexical_variety, 4),
        "phrase_repetition_ratio": round(phrase_repetition_ratio, 4),
    }


def compute_consensagent_style_score(dialogue_text: str) -> Dict[str, Any]:
    turns = _extract_turns(dialogue_text)
    sentences = _split_sentences(dialogue_text)
    num_sentences = max(1, len(sentences))
    agreement_count = sum(
        1 for s in sentences if any(p in s for p in AGREEMENT_PHRASES)
    )
    agreement_phrase_ratio = min(1.0, agreement_count / num_sentences)
    dialogue_lower = (dialogue_text or "").lower()
    has_disagreement = any(p in dialogue_lower for p in DISAGREEMENT_PHRASES)

    overlaps: List[float] = []
    for i in range(len(turns) - 1):
        ta = _filter_stopwords(_tokenize(turns[i]))
        tb = _filter_stopwords(_tokenize(turns[i + 1]))
        overlaps.append(_jaccard_overlap(ta, tb))
    inter_turn_lexical_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0

    sycophancy_risk = max(0.0, min(1.0, 0.5 * agreement_phrase_ratio + 0.5 * inter_turn_lexical_overlap))
    critical_engagement = 1.0 - sycophancy_risk
    if has_disagreement:
        critical_engagement = min(1.0, critical_engagement + 0.1)
    return {
        "sycophancy_risk": round(sycophancy_risk, 4),
        "critical_engagement": round(critical_engagement, 4),
    }


def compute_composite_quality_score(
    core_score: float, sycophancy_risk: float, critical_engagement: float
) -> float:
    return round(0.4 * core_score + 0.3 * (1.0 - sycophancy_risk) + 0.3 * critical_engagement, 4)


def score_utterance_legacy(
    text: str,
    history: List[str],
    speaker_name: str = "",
    listener_name: str = "",
    known_names: Optional[List[str]] = None,
) -> float:
    """Single-utterance gate used by DialogueEngine retries."""
    ok, _ = validate_utterance(
        text, speaker_name or "Speaker", listener_name or "Listener",
        DIALOGUE_MIN_WORDS, known_names,
    )
    if not ok:
        return 0.1
    words = _tokenize(text)
    if len(words) < DIALOGUE_MIN_WORDS:
        return 0.15
    core = compute_core_score(text, recent_utterances=history)
    cons = compute_consensagent_style_score(text)
    composite = compute_composite_quality_score(
        core["core_score"], cons["sycophancy_risk"], cons["critical_engagement"]
    )
    return composite


def should_regenerate(text: str, history: List[str]) -> bool:
    words = _tokenize(text)
    if len(words) < DIALOGUE_MIN_WORDS:
        return True
    core = compute_core_score(text, recent_utterances=history)
    cons = compute_consensagent_style_score(text)
    if core["core_score"] < CORE_REGENERATE_THRESHOLD:
        return True
    if cons["sycophancy_risk"] > SYCOPHANCY_REGENERATE_THRESHOLD:
        return True
    return False


def append_quality_trace(record: Dict[str, Any], trace_path: Optional[str] = None) -> None:
    """Append one NDJSON quality trace line (ponytail: optional debug file)."""
    path = trace_path or os.getenv("DIALOGUE_QUALITY_TRACE", "output/dialogue_quality.ndjson")
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        record.setdefault("timestamp", int(time.time() * 1000))
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
