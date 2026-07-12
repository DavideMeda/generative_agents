from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from core.personality.trait_schema import trait_get

ACTION_KEYS: list[str] = [
    "move_up",
    "move_down",
    "move_left",
    "move_right",
    "stay_put",
    "seek_social",
    "seek_poi",
    "avoid_crowd",
    "interact",
    "explore",
]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        if isinstance(value, float) and math.isnan(value):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


@dataclass
class NEATInputSpec:
    """Converts the live simulation state into a stable numeric vector."""

    size: int = 18

    def encode(self, agent: Any, world: Any, others: Iterable[Any]) -> np.ndarray:
        width = max(1.0, _safe_float(getattr(world, "width", 1), 1.0))
        height = max(1.0, _safe_float(getattr(world, "height", 1), 1.0))
        x, y = getattr(agent, "pos", (0, 0))
        pos_x = _clamp01(_safe_float(x) / max(1.0, width - 1.0))
        pos_y = _clamp01(_safe_float(y) / max(1.0, height - 1.0))

        nearest_agent_dist = 1.0
        social_density = 0.0
        others_list = list(others or [])
        for other in others_list:
            ox, oy = getattr(other, "pos", (x, y))
            dist = abs(_safe_float(ox) - _safe_float(x)) + abs(_safe_float(oy) - _safe_float(y))
            norm_dist = _clamp01(dist / max(1.0, width + height))
            nearest_agent_dist = min(nearest_agent_dist, norm_dist)
            if dist <= 4:
                social_density += 1.0
        social_density = _clamp01(social_density / max(1.0, len(others_list)))

        goal_dx = 0.5
        goal_dy = 0.5
        goal_dist = 1.0
        goal = getattr(agent, "goal_pos", None)
        if goal is None:
            goal = self._nearest_poi(agent, world)
        if goal is not None:
            gx, gy = goal
            goal_dx = _clamp01((_safe_float(gx) - _safe_float(x) + width) / (2.0 * width))
            goal_dy = _clamp01((_safe_float(gy) - _safe_float(y) + height) / (2.0 * height))
            dist = abs(_safe_float(gx) - _safe_float(x)) + abs(_safe_float(gy) - _safe_float(y))
            goal_dist = _clamp01(dist / max(1.0, width + height))

        traits = getattr(agent, "traits", {}) or {}
        emotions = getattr(agent, "emotions", {}) or {}
        vector = [
            pos_x,
            pos_y,
            1.0 - nearest_agent_dist,
            social_density,
            goal_dx,
            goal_dy,
            1.0 - goal_dist,
            trait_get(traits, "openness", 0.5),
            trait_get(traits, "conscientiousness", 0.5),
            trait_get(traits, "extraversion", 0.5),
            trait_get(traits, "agreeableness", 0.5),
            trait_get(traits, "neuroticism", 0.5),
            _clamp01((_safe_float(emotions.get("valence", 0.0)) + 1.0) / 2.0),
            _clamp01(emotions.get("arousal", 0.5)),
            _clamp01(emotions.get("stress", 0.3)),
            _clamp01(len(getattr(agent, "recent_positions", []) or []) / 10.0),
            1.0 if getattr(agent, "mission_id", None) else 0.0,
            1.0,
        ]
        arr = np.asarray(vector, dtype=np.float64)
        if arr.size < self.size:
            arr = np.pad(arr, (0, self.size - arr.size), constant_values=0.0)
        return arr[: self.size]

    def _nearest_poi(self, agent: Any, world: Any) -> Any:
        pois = getattr(world, "pois", []) or []
        if not pois:
            return None
        x, y = getattr(agent, "pos", (0, 0))
        best = None
        best_dist = None
        for poi in pois:
            try:
                px = int(poi.get("x"))
                py = int(poi.get("y"))
                dist = abs(px - int(x)) + abs(py - int(y))
                if best_dist is None or dist < best_dist:
                    best = (px, py)
                    best_dist = dist
            except Exception:
                continue
        return best


@dataclass
class NEATOutputSpec:
    """Converts network activations into the action dictionary expected by SimEngine."""

    keys: list[str] = field(default_factory=lambda: list(ACTION_KEYS))

    @property
    def size(self) -> int:
        return len(self.keys)

    def decode(self, values: Iterable[float]) -> dict[str, float]:
        arr = np.asarray(list(values), dtype=np.float64)
        if arr.size < self.size:
            arr = np.pad(arr, (0, self.size - arr.size), constant_values=0.0)
        arr = arr[: self.size]
        scores = 1.0 / (1.0 + np.exp(-np.clip(arr, -12.0, 12.0)))
        return {key: float(_clamp01(scores[idx])) for idx, key in enumerate(self.keys)}
