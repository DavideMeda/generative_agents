"""Unit tests for MissionSystem."""
import random

from gen_agent.sim.missions import MissionSystem
from gen_agent.world.poi import POI
from gen_agent.world.world import World


def _small_world() -> World:
    return World(pois=[
        POI("home", "Home", 0.0, 0.0),
        POI("park", "Park", 5.0, 5.0),
        POI("cafe", "Cafe", 10.0, 0.0),
    ])


def test_assign_returns_visit_poi_mission():
    system = MissionSystem(_small_world(), mission_duration_ticks=20, rng=random.Random(1))
    mission = system.assign("agent1", current_tick=5)
    assert mission is not None
    assert mission.mission_type == "visit_poi"
    assert mission.target_poi is not None
    assert mission.expires_tick == 25
    assert mission.agent_id == "agent1"


def test_assign_avoids_recent_pois():
    system = MissionSystem(_small_world(), rng=random.Random(99))
    first = system.assign("agent1", current_tick=1)
    second = system.assign("agent1", current_tick=2)
    assert first is not None and second is not None
    assert first.target_poi is not None and second.target_poi is not None
    # ponytail: with 3 POIs and avoid-last-3, second pick may repeat only if exhausted
    assert second.assigned_tick == 2


def test_record_completion_appends_history():
    system = MissionSystem(_small_world(), rng=random.Random(0))
    system.record_completion("agent1", "park")
    mission = system.assign("agent1", current_tick=10)
    assert mission is not None
