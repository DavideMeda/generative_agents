"""Tests for AssociativeMemoryBridge and StanfordCognitionBridge."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from gen_agent.integrations.stanford.cognitive import (
    AssociativeMemoryBridge,
    StanfordCognitionBridge,
)


def _make_memory():
    """Stub memory store compatible with MemoryProtocol."""
    mem = MagicMock()
    mem.store.return_value = "mem-id-1"
    record = MagicMock()
    record.content = "was at the cafe"
    mem.retrieve.return_value = [record]
    return mem


class TestAssociativeMemoryBridge:

    def _bridge(self, llm=None):
        return AssociativeMemoryBridge(
            agent_id="a1",
            agent_name="Alice",
            memory_store=_make_memory(),
            llm=llm,
        )

    def test_add_memory_calls_store(self):
        mem = _make_memory()
        b = AssociativeMemoryBridge("a1", "Alice", mem)
        result = b.add_memory("saw a bird", memory_type="observation", importance=4.0)
        mem.store.assert_called_once_with(
            agent_id="a1",
            content="saw a bird",
            memory_type="observation",
            importance=4.0,
        )
        assert result == "mem-id-1"

    def test_retrieve_memories_returns_contents(self):
        b = self._bridge()
        results = b.retrieve_memories("routine", top_k=3)
        assert results == ["was at the cafe"]

    def test_retrieve_memories_handles_exception(self):
        mem = _make_memory()
        mem.retrieve.side_effect = RuntimeError("db error")
        b = AssociativeMemoryBridge("a1", "Alice", mem)
        assert b.retrieve_memories("anything") == []

    def test_get_scratch_default_keys(self):
        b = self._bridge()
        scratch = b.get_scratch()
        assert "name" in scratch
        assert scratch["name"] == "Alice"
        assert "daily_plan" in scratch

    def test_set_and_get_scratch(self):
        b = self._bridge()
        b.set_scratch("mood", "happy")
        assert b.get_scratch()["mood"] == "happy"

    def test_update_scratch(self):
        b = self._bridge()
        b.update_scratch({"curr_tile": (5, 5), "mood": "calm"})
        s = b.get_scratch()
        assert s["curr_tile"] == (5, 5)
        assert s["mood"] == "calm"

    def test_generate_daily_plan_no_llm_returns_stub(self):
        b = self._bridge(llm=None)
        plan = b.generate_daily_plan({})
        assert isinstance(plan, list)
        assert len(plan) > 0

    def test_generate_daily_plan_with_llm(self):
        llm = MagicMock(return_value='{"plan_text":"go walk","steps":["walk"]}')
        b = self._bridge(llm=llm)
        # patch at the source module since it's imported inside the function
        with patch("gen_agent.integrations.stanford.structured_planner.generate_structured_plan") as mock_plan:
            mock_plan.return_value = {"steps": ["go to park"]}
            plan = b.generate_daily_plan({"location": "park"})
        assert plan == ["go to park"]

    def test_run_reflection_no_llm(self):
        b = self._bridge(llm=None)
        # patch at the source module since generate_reflection is imported inside the method
        with patch("gen_agent.memory.reflection.generate_reflection", return_value="I feel tired"):
            result = b.run_reflection()
        assert result == "I feel tired"

    def test_run_reflection_exception_returns_empty(self):
        mem = _make_memory()
        mem.retrieve.side_effect = RuntimeError("fail")
        b = AssociativeMemoryBridge("a1", "Alice", mem)
        result = b.run_reflection()
        assert result == ""


class TestStanfordCognitionBridge:

    def test_register_agent_creates_persona(self):
        bridge = StanfordCognitionBridge(memory_store=_make_memory())
        persona = bridge.register_agent("a1", "Alice")
        assert persona is not None
        assert persona._agent_name == "Alice"

    def test_register_agent_idempotent(self):
        bridge = StanfordCognitionBridge(memory_store=_make_memory())
        p1 = bridge.register_agent("a1", "Alice")
        p2 = bridge.register_agent("a1", "Alice")
        assert p1 is p2

    def test_get_persona_missing_returns_none(self):
        bridge = StanfordCognitionBridge(memory_store=_make_memory())
        assert bridge.get_persona("no_such_id") is None

    def test_tick_all_skips_non_multiple(self):
        bridge = StanfordCognitionBridge(memory_store=_make_memory())
        persona = bridge.register_agent("a1", "Alice")
        with patch.object(persona, "run_reflection") as mock_reflect:
            bridge.tick_all(tick=1)  # not multiple of 25
            mock_reflect.assert_not_called()

    def test_tick_all_runs_at_multiple_of_25(self):
        bridge = StanfordCognitionBridge(memory_store=_make_memory())
        persona = bridge.register_agent("a1", "Alice")
        with patch.object(persona, "run_reflection", return_value="meh") as mock_reflect:
            bridge.tick_all(tick=25)
            mock_reflect.assert_called_once()
