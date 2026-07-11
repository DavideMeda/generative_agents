"""Tests for per-agent SQLite persistence."""
from __future__ import annotations


class TestPerAgentPersistence:
    def test_creates_separate_dbs(self, tmp_path):
        from gen_agent.memory.manager import MemoryManager
        mm = MemoryManager(data_dir=str(tmp_path))
        mm.ensure_agent("agent_a")
        mm.ensure_agent("agent_b")
        assert (tmp_path / "agents" / "agent_a" / "memory.db").exists()
        assert (tmp_path / "agents" / "agent_b" / "memory.db").exists()

    def test_memories_isolated_per_agent(self, tmp_path):
        from gen_agent.interfaces.memory_protocol import MemoryQuery
        from gen_agent.memory.manager import MemoryManager
        mm = MemoryManager(data_dir=str(tmp_path))

        mm.store("agent_a", "Marco went to the library.", "observation", 5.0)
        mm.store("agent_b", "Lucia went to the cafe.", "observation", 5.0)

        recs_a = mm.retrieve(MemoryQuery(agent_id="agent_a", query_text="", top_k=10))
        recs_b = mm.retrieve(MemoryQuery(agent_id="agent_b", query_text="", top_k=10))

        contents_a = [r.content for r in recs_a]
        contents_b = [r.content for r in recs_b]

        assert any("Marco" in c for c in contents_a)
        assert not any("Marco" in c for c in contents_b)
        assert any("Lucia" in c for c in contents_b)

    def test_persistence_across_manager_instances(self, tmp_path):
        from gen_agent.interfaces.memory_protocol import MemoryQuery
        from gen_agent.memory.manager import MemoryManager

        mm1 = MemoryManager(data_dir=str(tmp_path))
        mm1.store("agent_a", "Persistent memory content.", "observation", 5.0)

        mm2 = MemoryManager(data_dir=str(tmp_path))
        recs = mm2.retrieve(MemoryQuery(agent_id="agent_a", query_text="", top_k=10))
        assert any("Persistent" in r.content for r in recs)
