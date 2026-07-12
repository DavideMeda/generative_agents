"""
RLIF — Reinforcement Learning from Interaction Feedback

After each interaction, updates a per-agent-pair reward signal.
Dynamically adjusts proximity radius and cooldown gaps:
  - High cumulative reward → agents seek each other more often (smaller gap)
  - Negative reward trend → agents avoid each other (larger gap / smaller radius)

Activated when ENABLE_RLIF=true.
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

_REWARD_MAP = {"positive": +1.0, "neutral": 0.0, "negative": -1.5}
_DECAY = 0.90   # per-interaction decay on cumulative reward


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


class RLIFEngine:
    """
    Tracks cumulative reward per agent pair and derives adaptive parameters.
    """

    def __init__(
        self,
        base_radius: float = 2.5,
        base_gap: int = 5,
    ) -> None:
        self._base_radius = base_radius
        self._base_gap = base_gap
        self._rewards: dict[tuple[str, str], float] = defaultdict(float)
        logger.info("RLIFEngine active (base_radius=%.1f, base_gap=%d)", base_radius, base_gap)

    def update(self, id_a: str, id_b: str, outcome: str) -> None:
        key = _pair_key(id_a, id_b)
        delta = _REWARD_MAP.get(outcome, 0.0)
        self._rewards[key] = self._rewards[key] * _DECAY + delta
        logger.debug("RLIF %s↔%s reward=%.2f", id_a, id_b, self._rewards[key])

    def radius_for(self, id_a: str, id_b: str) -> float:
        r = self._rewards[_pair_key(id_a, id_b)]
        # Positive reward → up to 1.5× base radius; negative → down to 0.5×
        scale = 1.0 + (r / 10.0)
        return max(0.5, min(2.0, scale)) * self._base_radius

    def gap_for(self, id_a: str, id_b: str) -> int:
        r = self._rewards[_pair_key(id_a, id_b)]
        # Positive reward → shorter gap (agents interact more often)
        gap = self._base_gap - int(r / 3.0)
        return max(1, min(self._base_gap * 2, gap))

    def top_pairs(self, n: int = 5) -> list[Any]:
        """Return n pairs with highest reward (for social learning)."""
        sorted_pairs = sorted(self._rewards.items(), key=lambda x: x[1], reverse=True)
        return sorted_pairs[:n]


def make_rlif_if_enabled(base_radius: float = 2.5, base_gap: int = 5) -> RLIFEngine | None:
    if os.getenv("ENABLE_RLIF", "false").lower() in ("1", "true", "yes"):
        return RLIFEngine(base_radius=base_radius, base_gap=base_gap)
    return None
