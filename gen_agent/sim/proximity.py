"""
Proximity detection for agent interactions.

Determines when two agents are close enough to interact,
and enforces a minimum cooldown between consecutive interactions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class ProximityConfig:
    interaction_radius: float = 2.0
    min_gap_ticks: int = 5  # minimum ticks between interactions for the same pair


class ProximityDetector:
    def __init__(self, config: ProximityConfig | None = None) -> None:
        self._cfg = config or ProximityConfig()
        # Maps frozenset({id_a, id_b}) -> last interaction tick
        self._last_interaction: Dict[frozenset, int] = {}

    def within_radius(
        self, pos_a: Tuple[float, float], pos_b: Tuple[float, float]
    ) -> bool:
        dx = pos_a[0] - pos_b[0]
        dy = pos_a[1] - pos_b[1]
        return math.hypot(dx, dy) <= self._cfg.interaction_radius

    def can_interact(self, id_a: str, id_b: str, current_tick: int) -> bool:
        key: frozenset = frozenset({id_a, id_b})
        last = self._last_interaction.get(key, -self._cfg.min_gap_ticks)
        return (current_tick - last) >= self._cfg.min_gap_ticks

    def record_interaction(self, id_a: str, id_b: str, tick: int) -> None:
        self._last_interaction[frozenset({id_a, id_b})] = tick
