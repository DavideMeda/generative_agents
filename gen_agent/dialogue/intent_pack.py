"""
Intent pack builder — derives a structured dialogue intent from Big Five traits,
emotions, and relationship data. Ported slim from Gen_Agent legacy.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

CANONICAL_TRAIT_KEYS = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")
_TRAIT_ALIASES = (
    ("openness",          ("openness", "apertura")),
    ("conscientiousness", ("conscientiousness",)),
    ("extraversion",      ("extraversion", "estroversione", "estroversion")),
    ("agreeableness",     ("agreeableness", "gradevolezza")),
    ("neuroticism",       ("neuroticism", "nevroticismo", "nevroticism")),
)


def trait_get(traits: Optional[Dict[str, Any]], canonical: str, default: float = 0.5) -> float:
    if not traits:
        return float(default)
    for canon, alts in _TRAIT_ALIASES:
        if canon != canonical:
            continue
        for alt in alts:
            if alt in traits:
                try:
                    return float(traits[alt])
                except (TypeError, ValueError):
                    return float(default)
        return float(default)
    return float(default)


def normalize_personality(traits: Optional[Dict[str, Any]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for canon, alts in _TRAIT_ALIASES:
        val = 0.5
        if traits:
            for alt in alts:
                if alt in traits:
                    try:
                        val = float(traits[alt])
                    except (TypeError, ValueError):
                        val = 0.5
                    break
        out[canon] = max(0.0, min(1.0, val))
    return out


_RE_CLEAN_MEM = re.compile(
    r"\[-?\d+T\d*::\d*Z?\]|(?:interaction in zone|interaction in zona)\s*'[^']*'\s*:|"
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?|"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def build_intent_pack(
    sp_traits: Optional[Dict[str, float]],
    li_traits: Optional[Dict[str, float]],
    rel_data: Optional[Dict[str, float]],
    sp_em: Optional[Dict[str, float]],
    sp_memories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Build a structured intent pack from speaker's Big Five, emotions, and relationship.
    Drives the LLM prompt toward personality-consistent behaviour.
    """
    traits = sp_traits or {}
    rels = rel_data or {}
    ems = sp_em or {}

    openness = trait_get(traits, "openness", 0.5)
    conscientiousness = trait_get(traits, "conscientiousness", 0.5)
    extraversion = trait_get(traits, "extraversion", 0.5)
    agreeableness = trait_get(traits, "agreeableness", 0.5)
    neuroticism = trait_get(traits, "neuroticism", 0.5)

    trust = float(rels.get("trust", 0.5))
    valence_rel = float(rels.get("valence", 0.0))
    arousal = float(ems.get("arousal", 0.5))
    stress = float(ems.get("stress", 0.3))

    rel_neg = valence_rel < -0.25
    low_trust = trust < 0.35
    high_neuro = neuroticism > 0.65
    low_agree = agreeableness < 0.4

    if rel_neg and low_trust and low_agree:
        stance = "provocative"
    elif rel_neg and low_trust:
        stance = "competitive"
    elif high_neuro or low_agree:
        stance = "defensive"
    elif openness > 0.75 and not rel_neg:
        stance = "analytical"
    elif extraversion > 0.72 and trust >= 0.3:
        stance = "energetic"
    else:
        stance = "cooperative"

    conflict_allowed = (agreeableness < 0.45 or valence_rel < -0.15
                        or trust < 0.35 or neuroticism > 0.7)
    tension_level = min(1.0, max(0.0,
        (1.0 - trust) * 0.3 + neuroticism * 0.25 + stress * 0.25 + max(0.0, -valence_rel) * 0.2))

    goal_map = {
        "competitive": "defend your position and challenge the other's point of view",
        "defensive": "protect yourself from criticism, stay cautious and measured",
        "analytical": "explore the topic with curiosity, propose new angles",
        "energetic": "guide the conversation, propose concrete next steps",
        "provocative": "challenge the other, push toward direct confrontation",
        "cooperative": "share perspectives and genuinely understand the other person",
    }
    goal = goal_map.get(stance, goal_map["cooperative"])

    if extraversion > 0.7 or arousal > 0.65:
        voice_style = "energetic"
    elif conscientiousness > 0.7:
        voice_style = "formal"
    elif openness > 0.75 or neuroticism < 0.35:
        voice_style = "reflective"
    else:
        voice_style = "direct"

    memory_anchors: List[str] = []
    if sp_memories:
        for mem in sp_memories[:4]:
            raw = str(mem).strip()
            clean = _RE_CLEAN_MEM.sub("", raw).strip(" .:, -")
            if len(clean) >= 12:
                memory_anchors.append(clean[:100] + ("..." if len(clean) > 100 else ""))
            if len(memory_anchors) >= 2:
                break

    forbidden: List[str] = []
    if not conflict_allowed:
        forbidden.extend(["explicit disagreement", "direct attack"])
    if stance in ("competitive", "provocative"):
        forbidden.extend(["shared solution", "common ground"])

    return {
        "goal": goal,
        "stance": stance,
        "tension_level": round(tension_level, 3),
        "conflict_allowed": conflict_allowed,
        "voice_style": voice_style,
        "memory_anchors": memory_anchors,
        "forbidden_patterns": forbidden,
    }


def has_explicit_disagreement(text: str) -> bool:
    return bool(re.search(
        r"\b(?:i disagree|i don'?t agree|i do not agree|i oppose|that'?s wrong|"
        r"i'?m not convinced|fundamentally disagree)\b",
        text or "", re.IGNORECASE))


def intent_pack_to_prompt_section(pack: Dict[str, Any], speaker_name: str) -> str:
    """Render an intent pack as a compact prompt section."""
    lines = [
        "CHARACTER GUIDANCE:",
        f"  Goal: {pack['goal']}",
        f"  Communication style: {pack['voice_style']} / {pack['stance']}",
        f"  Tension level: {pack['tension_level']:.2f}/1.0",
    ]
    if pack.get("memory_anchors"):
        lines.append("  Reference naturally (do not quote verbatim):")
        for anchor in pack["memory_anchors"]:
            lines.append(f"    - {anchor}")
    if pack.get("forbidden_patterns"):
        lines.append(f"  Avoid: {', '.join(pack['forbidden_patterns'])}")
    if pack.get("conflict_allowed"):
        lines.append("  Conflict is appropriate if it fits the situation.")
    else:
        lines.append("  Keep the exchange constructive, avoid direct attacks.")
    return "\n".join(lines)
