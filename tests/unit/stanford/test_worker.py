"""Tests for StanfordCognitionWorker — stub mode only (no Ollama, no LLM)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from gen_agent.integrations.stanford.worker import StanfordCognitionJob, StanfordCognitionWorker


def _make_worker(**kwargs):
    adapter = MagicMock()
    adapter._llm = None
    world = MagicMock()
    world.pois = []
    return StanfordCognitionWorker(adapter=adapter, world=world, **kwargs)


class TestStanfordCognitionWorker:

    def test_enqueue_returns_true(self):
        w = _make_worker()
        job = StanfordCognitionJob(agent_id="a1", tick=0)
        assert w.enqueue(job) is True

    def test_queue_size_increments(self):
        w = _make_worker(max_queue=10)
        w.enqueue(StanfordCognitionJob(agent_id="a1", tick=0))
        w.enqueue(StanfordCognitionJob(agent_id="a2", tick=1))
        assert w.queue_size() == 2

    def test_enqueue_full_returns_false(self):
        w = _make_worker(max_queue=1)
        w.enqueue(StanfordCognitionJob(agent_id="a1", tick=0))
        result = w.enqueue(StanfordCognitionJob(agent_id="a2", tick=1))
        assert result is False

    def test_start_stop(self):
        w = _make_worker()
        w.start()
        assert w._thread is not None
        assert w._thread.is_alive()
        w.stop()
        assert not w._thread.is_alive()

    def test_start_idempotent(self):
        w = _make_worker()
        w.start()
        t1 = w._thread
        w.start()  # second call must be noop
        assert w._thread is t1
        w.stop()

    def test_enqueue_bootstrap(self):
        w = _make_worker()
        ok = w.enqueue_bootstrap("agent_x", tick=5)
        assert ok is True
        job = w._q.get_nowait()
        assert job.reason == "bootstrap"
        assert job.agent_id == "agent_x"

    def test_bind_engine(self):
        w = _make_worker()
        mock_engine = MagicMock()
        mock_engine._agents = {}
        w.bind_engine(mock_engine)
        assert w._engine is mock_engine
        # _get_agent must now proxy to engine._agents
        result = w._get_agent("nonexistent")
        assert result is None

    def test_process_skips_missing_agent(self):
        w = _make_worker()
        w._get_agent = lambda aid: None  # always missing
        job = StanfordCognitionJob(agent_id="ghost", tick=0)
        # should not raise
        w._process(job)

    def test_process_with_mock_agent_no_llm(self):
        w = _make_worker()
        agent = MagicMock()
        agent.name = "Alice"
        agent.target_poi = None
        agent.extra = {}
        w._get_agent = lambda aid: agent

        with patch("gen_agent.integrations.stanford.worker.generate_structured_plan") as mock_plan:
            mock_plan.return_value = {"plan_text": "go to the park", "plan": []}
            with patch("gen_agent.integrations.stanford.worker.apply_plan_to_agent") as mock_poi:
                mock_poi.return_value = None
                job = StanfordCognitionJob(agent_id="a1", tick=1)
                w._process(job)
        mock_plan.assert_called_once()

    def test_is_busy_initially_false(self):
        w = _make_worker()
        assert w.is_busy() is False
