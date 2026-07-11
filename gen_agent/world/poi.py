"""Point Of Interest (POI) definition."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class POI:
    """A named location in the 2D world that agents can navigate to."""

    poi_id: str
    name: str
    x: float
    y: float
    tags: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.name} ({self.x:.1f}, {self.y:.1f})"
