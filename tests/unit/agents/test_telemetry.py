"""Unit tests for TelemetryReporter."""
from gen_agent.interfaces.sim_protocol import AgentConfig
from gen_agent.sim.engine import SimConfig, SimEngine
from gen_agent.telemetry.reporter import TelemetryReporter


def _run_sim(n_ticks: int = 3) -> TelemetryReporter:
    engine = SimEngine(SimConfig(interaction_radius=10.0, min_gap_ticks=1))
    engine.register_agent(AgentConfig("a1", "Alice", (0.0, 0.0)))
    engine.register_agent(AgentConfig("a2", "Bob", (1.0, 0.0)))

    reporter = TelemetryReporter(sim_id="test-run")
    reporter.start()
    for _ in range(n_ticks):
        result = engine.advance()
        reporter.record(result)
    return reporter


def test_report_tick_count():
    reporter = _run_sim(5)
    report = reporter.finish()
    assert report.total_ticks == 5


def test_report_has_interactions():
    reporter = _run_sim(3)
    report = reporter.finish()
    assert report.total_interactions >= 1


def test_report_to_json():
    reporter = _run_sim(2)
    report = reporter.finish()
    json_str = report.to_json()
    assert "sim_id" in json_str
    assert "total_ticks" in json_str


def test_save_to_file(tmp_path):
    reporter = _run_sim(2)
    out = str(tmp_path / "report.json")
    reporter.save(out)
    import json
    import pathlib
    data = json.loads(pathlib.Path(out).read_text())
    assert data["sim_id"] == "test-run"
