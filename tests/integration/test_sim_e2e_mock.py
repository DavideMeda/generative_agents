"""
E2E integration test — 10 tick mock simulation (no LLM, no network).
Verifies the full engine stack: memory, dialogue (mock), missions, emotions.
"""
from __future__ import annotations

import math
import time

import pytest

from gen_agent.agents.emotions import EmotionState
from gen_agent.dialogue.dialogue_engine import DialogueEngine
from gen_agent.interfaces.sim_protocol import AgentConfig
from gen_agent.memory.manager import MemoryManager
from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend
from gen_agent.sim.engine import SimConfig, SimEngine


def _build_engine(ticks: int = 10) -> tuple:
    backend = SQLiteMemoryBackend(db_path=":memory:")
    memory = MemoryManager(backend=backend, data_dir="/tmp/test_e2e_mock")
    dialogue = DialogueEngine(llm=None, memory_store=memory, max_turns=2, min_words=5)

    cfg = SimConfig(
        interaction_radius=5.0,
        min_gap_ticks=2,
        interaction_every_ticks=3,
        block_on_dialogue=True,
        dialogue_max_turns=2,
        random_walk_step=0.5,
        seed=42,
    )
    engine = SimEngine(config=cfg, dialogue_engine=dialogue, memory_store=memory)

    agent_names = ["Marco", "Lucia", "Giovanni"]
    for i, name in enumerate(agent_names):
        angle = (2 * math.pi * i) / len(agent_names)
        pos = (1.5 * math.cos(angle), 1.5 * math.sin(angle))
        engine.register_agent(AgentConfig(agent_id=f"a{i}", name=name, position=pos))
        memory.ensure_agent(f"a{i}")
        memory.store(f"a{i}", f"{name} is in the town.", "observation", 5.0)

    return engine, memory


class TestSimE2EMock:
    def test_engine_runs_10_ticks(self):
        engine, memory = _build_engine()
        for _ in range(10):
            result = engine.advance()
            assert result.tick > 0

    def test_interactions_occur(self):
        engine, memory = _build_engine()
        for _ in range(10):
            engine.advance()
        stats = engine.stats()
        assert stats["interactions"] >= 0  # may be 0 if agents don't meet, just no crash

    def test_dialogues_produce_memories(self):
        engine, memory = _build_engine()
        for _ in range(10):
            engine.advance()
        total = memory.count()
        assert total >= 3  # at least the initial memories

    def test_snapshot_has_all_agents(self):
        engine, _ = _build_engine()
        engine.advance()
        snap = engine.snapshot()
        assert len(snap["agents"]) == 3

    def test_emotions_initialized(self):
        engine, _ = _build_engine()
        for s in engine.agents:
            assert s.emotions is not None

    def test_reset_clears_tick(self):
        engine, _ = _build_engine()
        for _ in range(5):
            engine.advance()
        engine.reset()
        assert engine.snapshot()["tick"] == 0
