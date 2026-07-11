"""Background Stanford cognition worker — plans, reflections, POI goals."""
from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from gen_agent.integrations.stanford.plan_to_poi import apply_plan_to_agent
from gen_agent.integrations.stanford.structured_planner import generate_structured_plan

logger = logging.getLogger(__name__)


@dataclass
class StanfordCognitionJob:
    agent_id: str
    tick: int
    reason: str = "bootstrap"


class StanfordCognitionWorker:
    def __init__(
        self,
        *,
        adapter: Any,
        world: Any,
        memory_store: Any = None,
        get_agent: Callable[[str], Any] | None = None,
        max_queue: int = 200,
    ) -> None:
        self._adapter = adapter
        self._world = world
        self._memory = memory_store
        self._get_agent = get_agent
        self._q: queue.Queue[StanfordCognitionJob] = queue.Queue(maxsize=max_queue)
        self._stop = False
        self._thread: threading.Thread | None = None
        self._busy = False
        self._engine: Any = None

    def bind_engine(self, engine: Any) -> None:
        self._engine = engine
        self._get_agent = lambda aid: engine._agents.get(aid)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def enqueue_bootstrap(self, agent_id: str, tick: int = 0) -> bool:
        return self.enqueue(StanfordCognitionJob(agent_id=agent_id, tick=tick, reason="bootstrap"))

    def enqueue(self, job: StanfordCognitionJob) -> bool:
        try:
            self._q.put_nowait(job)
            return True
        except queue.Full:
            return False

    def queue_size(self) -> int:
        return self._q.qsize()

    def is_busy(self) -> bool:
        return self._busy

    def _loop(self) -> None:
        while not self._stop:
            try:
                job = self._q.get(timeout=0.5)
            except queue.Empty:
                continue
            self._busy = True
            try:
                self._process(job)
            except Exception as exc:
                logger.warning("Stanford job failed %s: %s", job.agent_id, exc)
            finally:
                self._busy = False

    def _process(self, job: StanfordCognitionJob) -> None:
        agent = self._get_agent(job.agent_id) if self._get_agent else None
        if agent is None:
            return
        name = getattr(agent, "name", job.agent_id)
        memories: list[str] = []
        if self._memory is not None:
            try:
                from gen_agent.interfaces.memory_protocol import MemoryQuery
                records = self._memory.retrieve(
                    MemoryQuery(agent_id=job.agent_id, query_text="plan", top_k=6)
                )
                memories = [r.content for r in records]
            except Exception:
                pass

        location = "town"
        target = getattr(agent, "target_poi", None)
        if target is not None:
            location = getattr(target, "name", str(target))

        llm = getattr(self._adapter, "_llm", None)
        poi_names = [
            str(getattr(p, "name", p))
            for p in (getattr(self._world, "pois", None) or [])
        ]
        plan = generate_structured_plan(
            llm, name, memories, job.tick, location, poi_names=poi_names or None
        )
        plan_text = str(plan.get("plan_text") or " ".join(str(p) for p in plan.get("plan", [])))

        rr_index = 0
        if self._engine is not None:
            rr_index = int(getattr(self._engine, "_plan_poi_rr", {}).get(job.agent_id, 0))

        if self._world is not None:
            matched = apply_plan_to_agent(
                agent, plan_text, self._world, rr_index=rr_index, allow_fallback=True
            )
            if matched:
                logger.debug("%s plan→POI %s", name, matched)
            if self._engine is not None and hasattr(self._engine, "note_plan_poi"):
                self._engine.note_plan_poi(plan_text, matched)
                if matched and hasattr(self._engine, "_plan_poi_rr"):
                    self._engine._plan_poi_rr[job.agent_id] = rr_index + 1
            extra = getattr(agent, "extra", None)
            if isinstance(extra, dict):
                extra["last_plan_tick"] = job.tick

        if self._memory is not None and plan_text:
            self._memory.store(
                agent_id=job.agent_id,
                content=f"Plan (tick {job.tick}): {plan_text[:300]}",
                memory_type="plan",
                importance=7.0,
                tick=job.tick,
            )

        if hasattr(self._adapter, "run_reflection"):
            self._adapter.run_reflection(job.agent_id, memories[:10])
