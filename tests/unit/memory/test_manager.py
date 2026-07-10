"""Unit tests for MemoryManager (in-memory SQLite)."""
import pytest

from gen_agent.interfaces.memory_protocol import MemoryQuery
from gen_agent.memory.manager import MemoryManager
from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend


@pytest.fixture
def manager(tmp_path):
    backend = SQLiteMemoryBackend(db_path=str(tmp_path / "test.db"))
    return MemoryManager(backend=backend, data_dir=str(tmp_path), reflection_trigger=100)


def test_store_returns_id(manager):
    mid = manager.store("agent1", "Alice saw a bird", "observation", 7.0)
    assert isinstance(mid, str) and len(mid) > 0


def test_retrieve_returns_stored(manager):
    manager.store("agent1", "Alice saw a bird", "observation", 7.0)
    results = manager.retrieve(MemoryQuery(agent_id="agent1", query_text="bird"))
    assert len(results) == 1
    assert "bird" in results[0].content


def test_retrieve_respects_agent_isolation(manager):
    manager.store("agent1", "Alice memory", "observation", 5.0)
    manager.store("agent2", "Bob memory", "observation", 5.0)
    results = manager.retrieve(MemoryQuery(agent_id="agent1", query_text="memory"))
    assert all(r.agent_id == "agent1" for r in results)


def test_retrieve_top_k(manager):
    for i in range(10):
        manager.store("agent1", f"memory {i}", "observation", float(i))
    results = manager.retrieve(MemoryQuery(agent_id="agent1", query_text="memory", top_k=3))
    assert len(results) <= 3


def test_delete_removes_memory(manager):
    mid = manager.store("agent1", "ephemeral", "observation", 3.0)
    manager.delete(mid, agent_id="agent1")  # must specify agent_id for per-agent backend
    results = manager.retrieve(MemoryQuery(agent_id="agent1", query_text="ephemeral"))
    assert len(results) == 0


def test_count(manager):
    assert manager.count("agent1") == 0
    manager.store("agent1", "x", "observation", 1.0)
    manager.store("agent1", "y", "observation", 2.0)
    assert manager.count("agent1") == 2


def test_invalid_importance_raises():
    with pytest.raises(ValueError):
        from gen_agent.memory.models import Memory
        Memory(agent_id="a", content="x", memory_type="observation", importance=11.0)
