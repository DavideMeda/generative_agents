"""
Big Five personality trait helpers.

Traits are stored as floats in [0, 1] keyed by canonical name.
Provides normalization, random generation, and trait-based behavior hints.
"""
from __future__ import annotations

import random
from typing import Dict

BIG_FIVE = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")

_ALIASES: Dict[str, str] = {
    "open": "openness",
    "conscientious": "conscientiousness",
    "extravert": "extraversion",
    "agreeable": "agreeableness",
    "neurotic": "neuroticism",
}


def normalize(traits: Dict[str, float]) -> Dict[str, float]:
    """Ensure all Big Five keys exist and values are clamped to [0, 1]."""
    out: Dict[str, float] = {}
    for key in BIG_FIVE:
        alias = _ALIASES.get(key, key)
        v = traits.get(key, traits.get(alias, 0.5))
        out[key] = max(0.0, min(1.0, float(v)))
    return out


def random_traits(rng: random.Random | None = None) -> Dict[str, float]:
    r = rng or random
    return {k: round(r.gauss(0.5, 0.15), 3) for k in BIG_FIVE}


def interaction_willingness(traits: Dict[str, float]) -> float:
    """
    Proxy for how likely an agent is to initiate interaction.
    High extraversion and agreeableness → more willing.
    """
    return (traits.get("extraversion", 0.5) * 0.6 + traits.get("agreeableness", 0.5) * 0.4)
