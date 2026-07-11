"""
2D world definition with POI management.

World provides:
  - bounding box (width × height)
  - list of named POIs
  - nearest_poi() helper used by SimEngine and MissionSystem
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from gen_agent.world.poi import POI


@dataclass
class World:
    width: float = 20.0
    height: float = 20.0
    pois: list[POI] = field(default_factory=list)

    def nearest_poi(
        self,
        pos: tuple[float, float],
        tag: str | None = None,
        exclude_id: str | None = None,
    ) -> POI | None:
        """Return the closest POI to pos, optionally filtered by tag."""
        candidates = [
            p for p in self.pois
            if p.poi_id != exclude_id
            and (tag is None or tag in p.tags)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda p: math.hypot(p.x - pos[0], p.y - pos[1]))

    def random_poi(self, rng: random.Random | None = None, tag: str | None = None) -> POI | None:
        """Return a random POI, optionally filtered by tag."""
        candidates = [p for p in self.pois if tag is None or tag in p.tags]
        if not candidates:
            return None
        return (rng or random).choice(candidates)

    def random_position(self, rng: random.Random | None = None) -> tuple[float, float]:
        r = rng or random
        return (r.uniform(0, self.width), r.uniform(0, self.height))


def seed_default_world() -> World:
    """
    Return a default 20×20 world with 8 POIs — usable without any config file.
    POI coordinates are spread so agents naturally pass through multiple locations.
    """
    pois = [
        POI("home",      "Home",      2.0,  2.0,  ["rest", "private"]),
        POI("library",   "Library",   5.0, 15.0,  ["study", "quiet"]),
        POI("park",      "Park",     10.0, 10.0,  ["social", "outdoor"]),
        POI("cafe",      "Cafe",     15.0,  5.0,  ["social", "food"]),
        POI("townhall",  "Town Hall", 10.0,  2.0,  ["civic", "meeting"]),
        POI("hospital",  "Hospital",  2.0, 15.0,  ["health"]),
        POI("market",    "Market",   18.0, 12.0,  ["food", "social"]),
        POI("school",    "School",    8.0,  8.0,  ["study", "social"]),
    ]
    return World(width=20.0, height=20.0, pois=pois)
