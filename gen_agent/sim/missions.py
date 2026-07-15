"""
Mission system — assigns concrete goals to agents.

Mission types:
  visit_poi   — navigate to a specific POI
  patrol_zone — visit multiple POIs in sequence (future)
  assist_ally — move toward another agent (future)

Usage:
    system = MissionSystem(world)
    mission = system.assign("agent1", current_tick=5)
    # -> Mission(target_poi=POI("library",...), expires_tick=35, ...)
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from gen_agent.world.poi import POI
from gen_agent.world.world import World


@dataclass
class Mission:
    mission_type: str                    # "visit_poi" | "patrol_zone" | "assist_ally"
    target_poi: POI | None
    assigned_tick: int
    expires_tick: int
    completed: bool = False
    agent_id: str = ""


class MissionSystem:
    """
    Assigns and tracks missions for all agents.

    Each call to assign() returns a new mission if the agent has none,
    or renews an expired/completed mission.

    ponytail: only visit_poi implemented — add patrol_zone when multi-step nav lands.
    """

    def __init__(
        self,
        world: World,
        mission_duration_ticks: int = 30,
        rng: random.Random | None = None,
    ) -> None:
        self._world = world
        self._duration = mission_duration_ticks
        self._rng = rng or random.Random()
        self._history: dict[str, list[str]] = {}  # agent_id -> [poi_ids visited]

    def assign(self, agent_id: str, current_tick: int) -> Mission | None:
        """Return a new mission for agent_id."""
        # Prefer a POI not recently visited
        visited = self._history.get(agent_id, [])
        candidates = [
            p for p in self._world.pois
            if p.poi_id not in visited[-3:]   # avoid last 3
        ]
        if not candidates:
            candidates = self._world.pois
        if not candidates:
            return None

        target = self._rng.choice(candidates)
        self._history.setdefault(agent_id, []).append(target.poi_id)

        return Mission(
            mission_type="visit_poi",
            target_poi=target,
            assigned_tick=current_tick,
            expires_tick=current_tick + self._duration,
            agent_id=agent_id,
        )

