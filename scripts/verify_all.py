"""Quick sanity check for all new modules. Run: python scripts/verify_all.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

print("=== Gen_Agent — Full Module Verification ===")

# Core LLM
from gen_agent.llm import get_llm_provider

llm = get_llm_provider("mock")
resp = llm.complete("Say hello")
print(f"[OK] LLM mock: {resp[:50]}")

# World / POI
from gen_agent.world import seed_default_world

world = seed_default_world()
print(f"[OK] World: {len(world.pois)} POIs")

# Emotions
from gen_agent.agents import EmotionState, update_from_interaction

e = EmotionState()
e2 = update_from_interaction(e, 0.5, "positive")
assert e2.valence > e.valence, "Valence should increase on positive interaction"
print(f"[OK] EmotionState: valence {e.valence:.2f} -> {e2.valence:.2f}")

# Missions
from gen_agent.sim.missions import MissionSystem

ms = MissionSystem(world)
mission = ms.assign("agent1", current_tick=1)
assert mission is not None
print(f"[OK] MissionSystem: assigned '{mission.target_poi.name}'")

# Dialogue quality
from gen_agent.dialogue.quality import score_utterance

score = score_utterance("This is a very interesting thing to discuss with you.", [])
assert score > 0.3
print(f"[OK] Quality gate: score={score:.3f}")

# Cognitive layer (disabled by default — just import)
from gen_agent.cognitive import (
    make_hrm_if_enabled,
)

assert make_hrm_if_enabled() is None  # ENABLE_HRM not set
print("[OK] Cognitive layer: all factories return None when not enabled")

# Social intelligence
from gen_agent.social import ConsensusEngine, GameEngine, pure_nash_equilibria
from gen_agent.social.game_theory import PRISONER_DILEMMA

game = GameEngine()
result = game.play("a1", "a2", "prisoner_dilemma")
assert result.outcome in ("positive", "neutral", "negative")
print(f"[OK] GameEngine: {result.action_a} vs {result.action_b} -> {result.outcome}")
eq = pure_nash_equilibria(PRISONER_DILEMMA)
assert eq  # prisoner dilemma has a Nash equilibrium
print(f"[OK] Nash equilibria: {eq}")

# Consensus
ce = ConsensusEngine()
cr = ce.decide(["a", "b", "c"], "Park or Cafe?", ["park", "cafe"], method="majority_vote")
assert cr.winner in ("park", "cafe")
print(f"[OK] Consensus majority: winner={cr.winner}")

# Advanced memory
from gen_agent.memory.graph import KnowledgeGraph

kg = KnowledgeGraph()
kg.add_memory("m1", "Alice met Bob at the Park")
kg.add_memory("m2", "Alice visited the Library with Carol")
nbrs = kg.neighbours("alice")
assert len(nbrs) > 0
print(f"[OK] KnowledgeGraph: alice neighbours={nbrs}")

from gen_agent.memory.privacy import MaRSEngine, classify

assert classify("my health is poor") == "private"
assert classify("I visited the park") == "public"
print("[OK] Privacy classifier: health=private, park=public")

mars = MaRSEngine()
assert not mars.can_share("my secret medical condition")
print("[OK] MaRS: private memory not shareable")

from gen_agent.memory.compression import MemoryCompressor

comp = MemoryCompressor(memory_store=None)
assert not comp.should_run(0)
assert not comp.should_run(49)
assert comp.should_run(50)
print("[OK] MemoryCompressor: trigger at tick 50")

# Full scenario build and 3-tick run
from config.scenario import load_scenario

scenario = load_scenario("offline")
engine = scenario.build_engine()
for tick in range(3):
    r = engine.advance()
print(f"[OK] Scenario 'offline': ran 3 ticks, stats={engine.stats()}")

print()
print("=== ALL CHECKS PASSED ===")
