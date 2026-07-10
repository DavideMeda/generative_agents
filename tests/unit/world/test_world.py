"""Unit tests for World and POI."""
import random

from gen_agent.world.poi import POI
from gen_agent.world.world import World, seed_default_world


def test_poi_str():
    poi = POI("cafe", "Cafe", 1.5, 2.0)
    assert "Cafe" in str(poi)
    assert "1.5" in str(poi)


def test_nearest_poi_picks_closest():
    world = World(pois=[
        POI("a", "A", 0.0, 0.0),
        POI("b", "B", 10.0, 10.0),
    ])
    nearest = world.nearest_poi((1.0, 1.0))
    assert nearest is not None
    assert nearest.poi_id == "a"


def test_nearest_poi_filters_by_tag():
    world = World(pois=[
        POI("lib", "Library", 0.0, 0.0, ["study"]),
        POI("park", "Park", 1.0, 1.0, ["social"]),
    ])
    nearest = world.nearest_poi((0.5, 0.5), tag="study")
    assert nearest is not None
    assert nearest.poi_id == "lib"


def test_seed_default_world_has_eight_pois():
    world = seed_default_world()
    assert len(world.pois) == 8
    assert world.width == 20.0


def test_random_poi_uses_rng():
    world = seed_default_world()
    rng = random.Random(42)
    a = world.random_poi(rng=rng)
    rng = random.Random(42)
    b = world.random_poi(rng=rng)
    assert a is not None and b is not None
    assert a.poi_id == b.poi_id
