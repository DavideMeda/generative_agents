"""
SEAL — Social Emotional Adaptation Layer

Slowly adjusts Big Five traits based on accumulated interaction history.
Implements personality plasticity: repeated positive/negative experiences
shift trait values, simulating long-term behavioural change.

Update rules (small increments, capped per tick):
  positive outcome → agreeableness ↑, neuroticism ↓ slightly
  negative outcome → neuroticism ↑, agreeableness ↓ slightly
  many interactions → extraversion ↑ (social exposure)

Activated when ENABLE_SEAL=true.
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_STEP = 0.002       # max per-interaction trait change
_CLAMP = (0.0, 1.0)


def _clamp(v: float) -> float:
    return max(_CLAMP[0], min(_CLAMP[1], v))


class SEALEnhancer:
    """
    Computes and applies incremental trait updates after interactions.
    Stores interaction counts to derive extraversion drift.
    """

    def __init__(self) -> None:
        self._interaction_count: Dict[str, int] = defaultdict(int)
        logger.info("SEALEnhancer active")

    def update_traits(
        self,
        agent_id: str,
        traits: Dict[str, float],
        outcome: str,
    ) -> None:
        """
        Mutate traits in-place (small step) based on interaction outcome.
        traits is the _AgentState.traits dict — mutated directly.
        """
        self._interaction_count[agent_id] += 1

        if outcome == "positive":
            traits["agreeableness"] = _clamp(traits.get("agreeableness", 0.5) + _STEP)
            traits["neuroticism"] = _clamp(traits.get("neuroticism", 0.5) - _STEP * 0.5)
        elif outcome == "negative":
            traits["neuroticism"] = _clamp(traits.get("neuroticism", 0.5) + _STEP)
            traits["agreeableness"] = _clamp(traits.get("agreeableness", 0.5) - _STEP * 0.5)

        # Social exposure raises extraversion slowly
        count = self._interaction_count[agent_id]
        if count % 20 == 0:
            traits["extraversion"] = _clamp(traits.get("extraversion", 0.5) + _STEP * 0.5)
            logger.debug("SEAL %s extraversion → %.3f", agent_id, traits["extraversion"])


def make_seal_if_enabled() -> Optional[SEALEnhancer]:
    if os.getenv("ENABLE_SEAL", "false").lower() in ("1", "true", "yes"):
        return SEALEnhancer()
    return None
