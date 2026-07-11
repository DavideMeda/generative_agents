"""Utility comuni per tutti i benchmark — metadata e output JSON."""
from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output" / "benchmarks"


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def make_meta(preset: str, model: str = "stub") -> dict[str, Any]:
    return {
        "commit": _git_commit(),
        "preset": preset,
        "model": model,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "python": sys.version,
    }


def save_result(name: str, result: dict[str, Any]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR / f"{name}_{ts}.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"[benchmark] saved -> {out}")
    return out


def simple_engine(n_agents: int = 3, seed: int = 42) -> Any:
    """Build a minimal stub SimEngine (no LLM, no Ollama required)."""
    from gen_agent.interfaces.sim_protocol import AgentConfig
    from gen_agent.sim.engine import SimConfig, SimEngine

    cfg = SimConfig(
        block_on_dialogue=False,
        missions_enabled=False,
        seed=seed,
        interaction_every_ticks=9999,  # no dialogues
    )
    engine = SimEngine(config=cfg)
    for i in range(n_agents):
        engine.register_agent(AgentConfig(
            agent_id=f"agent_{i}",
            name=f"Agent{i}",
            position=(float(i * 2), 0.0),
        ))
    return engine
