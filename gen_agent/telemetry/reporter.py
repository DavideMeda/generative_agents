"""
Telemetry and reporting for Gen_Agent simulations.

Collects per-tick metrics and produces JSON-serialisable reports.
No external dependencies — structured logging only.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from gen_agent.interfaces.sim_protocol import TickResult

logger = logging.getLogger(__name__)


@dataclass
class TickMetrics:
    tick: int
    timestamp: float
    event_count: int
    interaction_count: int
    agent_count: int
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimReport:
    sim_id: str
    started_at: float
    finished_at: float
    total_ticks: int
    total_interactions: int
    ticks: list[TickMetrics] = field(default_factory=list)

    @property
    def duration_sec(self) -> float:
        return self.finished_at - self.started_at

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class TelemetryReporter:
    """
    Collects metrics across simulation ticks and produces a final report.

    Usage:
        reporter = TelemetryReporter(sim_id="run-001")
        reporter.start()
        for _ in range(n_ticks):
            result = engine.advance()
            reporter.record(result)
        report = reporter.finish()
        print(report.to_json())
    """

    def __init__(self, sim_id: str | None = None) -> None:
        self._sim_id = sim_id or f"sim-{int(time.time())}"
        self._started_at: float = 0.0
        self._ticks: list[TickMetrics] = []

    def start(self) -> None:
        self._started_at = time.time()
        self._ticks.clear()
        logger.info("Telemetry started for sim_id=%s", self._sim_id)

    def record(self, result: TickResult) -> None:
        interactions = [e for e in result.events if e.get("type") == "interaction"]
        metrics = TickMetrics(
            tick=result.tick,
            timestamp=time.time(),
            event_count=len(result.events),
            interaction_count=len(interactions),
            agent_count=len(result.agent_states),
        )
        self._ticks.append(metrics)

    def finish(self) -> SimReport:
        finished_at = time.time()
        return SimReport(
            sim_id=self._sim_id,
            started_at=self._started_at,
            finished_at=finished_at,
            total_ticks=len(self._ticks),
            total_interactions=sum(m.interaction_count for m in self._ticks),
            ticks=self._ticks,
        )

    def save(self, path: str) -> None:
        """Write the current report to a JSON file."""
        report = self.finish()
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report.to_json(), encoding="utf-8")
        logger.info("Report saved to %s", out)
