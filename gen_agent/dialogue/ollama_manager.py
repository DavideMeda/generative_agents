"""
Slim Ollama manager — wraps the LLM callable with retry/timeout logic.
Ported from Gen_Agent legacy ollama_dialogue_manager.py (English-only).
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Patterns that indicate the model leaked meta-commentary
_META_PATTERNS = re.compile(
    r"\b(?:as an ai|i am an ai|language model|llm|i cannot generate|"
    r"here is a possible|this is a dialogue|prompt:|note:|assistant:|"
    r"simulation|waking up|woke up|virtual reality|sleep state|npc|"
    r"i'?m not able to|i'?m unable to)\b",
    re.IGNORECASE,
)

# Patterns for obvious Italian contamination
_ITALIAN_PATTERNS = re.compile(
    r"\b(?:ciao|sono|davvero|anche|questo|quella|perché|molto|grazie|"
    r"stai|ecco|uscito|confuso|posso|devo|ancora|quindi|stiamo|siamo|"
    r"capisco|allora|purtroppo|prego|buongiorno|buonasera)\b",
    re.IGNORECASE,
)


def clean_dialogue_output(raw: str, speaker_name: str = "") -> str:
    """Remove common LLM artefacts from a dialogue response."""
    text = raw.strip()
    # Strip leading "Name: " label if present
    text = re.sub(r"^[A-Za-z][A-Za-z '-]*:\s*", "", text)
    # Strip stage directions like (smiles) or *nodding*
    text = re.sub(r"\([^)]{1,60}\)", "", text)
    text = re.sub(r"\*[^*]{1,60}\*", "", text)
    # Collapse excessive whitespace
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def is_output_valid(text: str, min_words: int = 10) -> bool:
    """Return True if the utterance passes basic sanity checks."""
    words = text.split()
    if len(words) < min_words:
        return False
    if _META_PATTERNS.search(text):
        return False
    italian_hits = len(_ITALIAN_PATTERNS.findall(text))
    if italian_hits >= 2:
        return False
    return True


def build_ollama_prompt(
    speaker_name: str,
    listener_name: str,
    memory_snippets: list,
    location: str,
    history: str,
    scenario: str,
    min_words: int,
    intent_section: str = "",
    retry_hint: str = "",
    traits: dict[str, float] | None = None,
    emotions: dict[str, float] | None = None,
) -> str:
    """Build a full LLM prompt with intent pack, traits, and emotion context."""
    memories = "\n".join(f"  - {m}" for m in memory_snippets) or "  - none"

    # Brief personality hint (2-3 words max, not verbose)
    personality_line = ""
    if traits:
        dominant = max(traits, key=traits.get)  # type: ignore[arg-type]
        personality_line = f"Your dominant trait: {dominant} ({traits[dominant]:.1f}/1.0)."

    emotion_line = ""
    if emotions:
        valence = emotions.get("valence", 0.0)
        mood = "good mood" if valence > 0.2 else ("tense" if valence < -0.2 else "neutral mood")
        emotion_line = f"Your current mood: {mood}."

    return (
        f"You are {speaker_name}, a resident of a small town.\n"
        f"You are talking face-to-face with {listener_name}.\n"
        f"Your name is {speaker_name}. Their name is {listener_name}.\n"
        f"Address {listener_name} by name in your first sentence — never use someone else's name.\n\n"
        f"SCENE: {scenario}\n"
        f"LOCATION: {location}\n"
        f"{personality_line}\n"
        f"{emotion_line}\n\n"
        f"{intent_section}\n\n"
        f"YOUR RECENT MEMORIES:\n{memories}\n\n"
        f"CONVERSATION SO FAR:\n{history or '(just starting)'}\n\n"
        "=" * 60 + "\n"
        "STRICT RULES (violating any rule = bad output):\n"
        f"- Write ONLY in English. Zero Italian words.\n"
        f"- Minimum {min_words} words, maximum 120 words.\n"
        "- You are a real person. Do NOT act like an AI.\n"
        "- NEVER mention: simulation, AI, language model, prompts, virtual reality, NPC, sleep state.\n"
        "- No stage directions, no asterisk actions, no parenthetical notes.\n"
        "- Do NOT write your own name as a label (e.g. don't start with 'Name:').\n"
        "- Natural imperfect spoken dialogue only.\n"
        f"{retry_hint}\n\n"
        f"Now reply as {speaker_name} speaking to {listener_name}:\n"
    )
