"""Dialogue output guards — meta, identity, language (ported from legacy Gen_Agent)."""
from __future__ import annotations

import re

# Italian markers — reject if too many appear in output
_ITALIAN_MARKERS = re.compile(
    r"\b("
    r"ciao|sono|cred[o|o]|davvero|felice|anche|questa|questo|quello|perch[eé]|"
    r"molto|bene|grazie|stai|come stai|ecco|stavo|uscito|confuso|parlare|"
    r"finalmente|sembra|dell['']|nell['']|all['']|un po|stato di sonno|"
    r"mi sento|ti senti|abbiamo|siete|siamo|vorrei|posso|devo|ancora|"
    r"ragazza|ragazzo|signora|signore|buongiorno|buonasera|certo|esatto"
    r")\b",
    re.IGNORECASE,
)

_META_PATTERNS = re.compile(
    r"("
    r"\bsimulation\b|\blanguage model\b|\bllm\b|\bas an ai\b|\bas a language\b|"
    r"\bthis prompt\b|\bmeta[\s-]?comment|\bgenerative agent\b|"
    r"\bcomputational agent\b|\bvirtual assistant\b|\bchatbot\b|"
    r"\bstate of sleep\b|\bwaking up\b|\bjust woke\b|\bwoke up\b|"
    r"\bstato di sonno\b|\bappena uscit[oa]\b|"
    r"\bi am an ai\b|\bi'm an ai\b|\bi am a bot\b|"
    r"\bnpc\b|\brole[\s-]?play\b|\bcharacter in a game\b|"
    r"\bvirtual reality\b|\bvr experience\b|\bvr headset\b|"
    r"\bi cannot generate\b|\bi can't generate\b|\bhere is a possible\b|"
    r"\bi hope this response\b|\bsure[,!]?\s+here\b"
    r")",
    re.IGNORECASE,
)

_GREETING = re.compile(
    r"(?i)\b(hi|hello|hey|dear|ciao|good morning|good afternoon|good evening)\s+([A-Za-z][A-Za-z'-]*)"
)

_SPEAKER_PREFIX = re.compile(r"^[\w][\w _'-]*:\s*", re.IGNORECASE)
_STAGE_DIRECTION = re.compile(r"\([^)]{1,60}\)")
_AROUSAL_TAG = re.compile(r"\(.*?(arousal|valence|stress).*?\)", re.IGNORECASE)
_LEADING_QUOTES = re.compile(r'^["“”\']+|["“”\']+$')


def clean_utterance(text: str, speaker_name: str) -> str:
    """Strip labels, stage directions, and duplicate speaker prefixes."""
    if not text:
        return ""
    t = text.strip()
    # Remove wrapping quotes
    t = _LEADING_QUOTES.sub("", t).strip()
    # Drop leading "Speaker:" if model echoed the label
    for _ in range(2):
        t2 = _SPEAKER_PREFIX.sub("", t).strip()
        if t2 == t:
            break
        t = t2
    # Remove duplicate "Marco: Marco:"
    dup = re.compile(rf"^{re.escape(speaker_name)}\s*:\s*{re.escape(speaker_name)}\s*:", re.I)
    t = dup.sub(f"{speaker_name}: ", t)
    t = _AROUSAL_TAG.sub("", t)
    t = _STAGE_DIRECTION.sub("", t).strip()
    return t.strip()


def detect_italian(text: str, threshold: int = 2) -> bool:
    return len(_ITALIAN_MARKERS.findall(text or "")) >= threshold


def detect_meta(text: str) -> bool:
    return bool(_META_PATTERNS.search(text or ""))


def detect_wrong_addressee(
    text: str,
    listener_name: str,
    known_names: list[str] | None = None,
) -> bool:
    """True if the utterance greets or addresses someone other than the listener."""
    if not text or not listener_name:
        return False
    listener = listener_name.strip().lower()
    known = {n.strip().lower() for n in (known_names or []) if n}
    for match in _GREETING.finditer(text):
        addressed = match.group(2).strip().lower()
        if addressed == listener:
            continue
        if known and addressed in known:
            return True
    # Direct vocative mid-sentence: "..., Anna," when listener is Elena
    for name in known:
        if name == listener:
            continue
        if re.search(rf"(?i)\b{re.escape(name)}\b", text[:80]):
            # Only flag if used as addressee near start
            if re.search(rf"(?i)(^|[,.!?\s])({re.escape(name)})([,!?]|\s)", text[:100]):
                return True
    return False


def validate_utterance(
    text: str,
    speaker_name: str,
    listener_name: str,
    min_words: int = 25,
    known_names: list[str] | None = None,
) -> tuple[bool, str]:
    cleaned = clean_utterance(text, speaker_name)
    words = cleaned.split()
    if len(words) < min_words:
        return False, f"too short ({len(words)} words, min={min_words})"
    if detect_meta(cleaned):
        return False, "meta-commentary detected"
    if detect_italian(cleaned):
        return False, "non-English (Italian) detected"
    if detect_wrong_addressee(cleaned, listener_name, known_names):
        return False, f"wrong addressee (expected {listener_name})"
    return True, ""


def build_retry_hint(
    reason: str,
    speaker_name: str,
    listener_name: str,
    min_words: int,
) -> str:
    return (
        f"\n\nIMPORTANT — previous attempt was invalid ({reason}). "
        f"You are {speaker_name}. You are speaking ONLY to {listener_name}. "
        f"Address them as {listener_name}, never another name. "
        f"Write at least {min_words} words in clear English only. "
        "No Italian. No meta-commentary about AI, simulation, prompts, or waking up. "
        "Dialogue only — no stage directions or parentheticals."
    )


def sanitize_memory_for_prompt(content: str) -> str:
    """Drop memories that would poison the prompt with meta or Italian."""
    if not content or not content.strip():
        return ""
    if detect_meta(content):
        return ""
    if detect_italian(content, threshold=3):
        return ""
    return content.strip()[:200]
