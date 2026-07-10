"""Tests for memory reflection and consolidation."""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from gen_agent.memory.manager import MemoryManager
from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend
from gen_agent.memory.reflection import generate_reflection
from gen_agent.interfaces.memory_protocol import MemoryRecord
import time


def _make_record(agent_id: str, content: str, importance: float = 5.0,
                 memory_type: str = "observation") -> MemoryRecord:
    return MemoryRecord(
        memory_id=f"test-{content[:10].replace(' ', '_')}",
        agent_id=agent_id,
        content=content,
        memory_type=memory_type,
        importance=importance,
        created_at=time.time(),
        last_accessed=time.time(),
    )


class TestReflectionGeneration:
    def test_reflection_without_llm(self):
        records = [
            _make_record("a1", "Walked to the park and met Lucia.", 6.0),
            _make_record("a1", "Had a conversation about the new library opening.", 7.0),
        ]
        text = generate_reflection("a1", "Marco", records, llm=None)
        assert isinstance(text, str)
        assert len(text) > 10

    def test_reflection_with_no_memories(self):
        text = generate_reflection("a1", "Marco", [], llm=None)
        assert isinstance(text, str)
        assert len(text) > 5

    def test_llm_reflection_fallback_on_error(self):
        def bad_llm(prompt):
            raise RuntimeError("LLM unavailable")

        records = [_make_record("a1", "Something happened.", 5.0)]
        text = generate_reflection("a1", "Marco", records, llm=bad_llm)
        assert isinstance(text, str)


class TestMemoryManagerReflection:
    def test_reflection_triggered_on_modulo(self):
        backend = SQLiteMemoryBackend(db_path=":memory:")
        mm = MemoryManager(backend=backend, reflection_trigger=3)
        mm.ensure_agent("a1")

        for i in range(3):
            mm.store("a1", f"Event {i} happened today in the town square.", "observation", 5.0)

        stats = mm.reflection_stats()
        assert stats["total_reflections"] >= 1

    def test_no_reflection_below_trigger(self):
        backend = SQLiteMemoryBackend(db_path=":memory:")
        mm = MemoryManager(backend=backend, reflection_trigger=10)
        mm.ensure_agent("a1")

        for i in range(2):
            mm.store("a1", f"Event {i}", "observation", 5.0)

        stats = mm.reflection_stats()
        assert stats["total_reflections"] == 0

    def test_salience_triggers_reflection(self):
        backend = SQLiteMemoryBackend(db_path=":memory:")
        mm = MemoryManager(backend=backend, reflection_trigger=100)  # disable modulo
        mm.ensure_agent("a1")

        # Add base memories
        for i in range(3):
            mm.store("a1", f"Ordinary event {i}", "observation", 4.0)
        # High-importance memory should trigger salience reflection
        mm.store("a1", "Something extremely important happened!", "observation", 8.0)

        stats = mm.reflection_stats()
        assert stats["total_reflections"] >= 1

    def test_per_agent_db_created(self, tmp_path):
        mm = MemoryManager(data_dir=str(tmp_path))
        mm.ensure_agent("agent_xyz")
        assert (tmp_path / "agents" / "agent_xyz" / "memory.db").exists()

    def test_social_scope_stores_and_retrieves(self):
        backend = SQLiteMemoryBackend(db_path=":memory:")
        mm = MemoryManager(backend=backend)
        mm.ensure_agent("a1")

        mm.store("a1", "Had a chat with Lucia at the cafe.", "social", 6.0)
        from gen_agent.interfaces.memory_protocol import MemoryQuery
        records = mm.retrieve(MemoryQuery(
            agent_id="a1", query_text="", top_k=5,
            memory_types=["social"]
        ))
        assert any(r.memory_type == "social" for r in records)
