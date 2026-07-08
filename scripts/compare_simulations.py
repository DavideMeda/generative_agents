#!/usr/bin/env python3
"""
Compare Nuovo Gen_Agent vs legacy Gen_Agent blocking simulations.

Runs legacy with blocking_balanced preset (100 ticks, 5 agents) then prints
side-by-side metrics against the new project's JSON report.

Usage:
  python scripts/compare_simulations.py
  python scripts/compare_simulations.py --skip-legacy   # only print new report
  python scripts/compare_simulations.py --skip-new      # only run legacy
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY_ROOT = ROOT.parent / "Gen_Agent"
NEW_REPORT = ROOT / "output" / "sim_blocking_100_new.json"
LEGACY_REPORT_GLOB = "report_test_*ticks*.json"


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def find_latest_legacy_report() -> Path | None:
    runs = sorted(LEGACY_ROOT.glob("runs/**/" + LEGACY_REPORT_GLOB), reverse=True)
    if not runs:
        runs = sorted(LEGACY_ROOT.glob("**/report_test_*100ticks*.json"), reverse=True)
    return runs[0] if runs else None


def extract_legacy_metrics(report: dict) -> dict:
    """Normalize legacy report fields to comparable keys."""
    stats = report.get("statistics", report)
    return {
        "project": "Gen_Agent (legacy)",
        "ticks": stats.get("total_ticks", stats.get("planned_ticks", report.get("planned_ticks"))),
        "agents": stats.get("agent_count", report.get("agent_count")),
        "interactions": stats.get("total_interactions", stats.get("interactions", 0)),
        "dialogues": stats.get("total_dialogues", stats.get("dialogues", 0)),
        "dialogue_utterances": stats.get("dialogue_utterances", 0),
        "missions_completed": stats.get("missions_completed", stats.get("poi_visits", 0)),
        "memories_total": stats.get("total_memories", stats.get("memories", 0)),
        "real_time_sec": round(report.get("runtime_s", report.get("real_time_sec", 0)), 2),
        "ollama_model": report.get("ollama_model", "n/a"),
        "preset": report.get("preset", "blocking_balanced"),
        "block_on_dialogue": report.get("block_on_dialogue", True),
    }


def extract_new_metrics(report: dict) -> dict:
    return {
        "project": report.get("project", "Nuovo Gen_Agent"),
        "ticks": report.get("final_tick", report.get("ticks_requested")),
        "agents": report.get("agents"),
        "interactions": report.get("interactions", 0),
        "dialogues": report.get("dialogues", 0),
        "dialogue_utterances": report.get("dialogue_utterances", 0),
        "missions_completed": report.get("missions_completed", 0),
        "memories_total": report.get("memories_total", 0),
        "real_time_sec": report.get("real_time_sec", 0),
        "ollama_model": report.get("ollama_model", "n/a"),
        "preset": report.get("scenario", "blocking_100"),
        "block_on_dialogue": report.get("block_on_dialogue", True),
    }


def print_comparison(new_m: dict, legacy_m: dict | None) -> None:
    rows = [
        ("Progetto", new_m["project"], legacy_m["project"] if legacy_m else "n/a"),
        ("Preset / scenario", new_m["preset"], legacy_m["preset"] if legacy_m else "n/a"),
        ("Agenti", new_m["agents"], legacy_m["agents"] if legacy_m else "n/a"),
        ("Tick completati", new_m["ticks"], legacy_m["ticks"] if legacy_m else "n/a"),
        ("Dialoghi bloccanti", new_m["block_on_dialogue"], legacy_m["block_on_dialogue"] if legacy_m else "n/a"),
        ("Modello Ollama", new_m["ollama_model"], legacy_m["ollama_model"] if legacy_m else "n/a"),
        ("Interazioni", new_m["interactions"], legacy_m["interactions"] if legacy_m else "n/a"),
        ("Dialoghi", new_m["dialogues"], legacy_m["dialogues"] if legacy_m else "n/a"),
        ("Turni dialogo", new_m["dialogue_utterances"], legacy_m["dialogue_utterances"] if legacy_m else "n/a"),
        ("Missioni completate", new_m["missions_completed"], legacy_m["missions_completed"] if legacy_m else "n/a"),
        ("Memorie totali", new_m["memories_total"], legacy_m["memories_total"] if legacy_m else "n/a"),
        ("Tempo reale (s)", new_m["real_time_sec"], legacy_m["real_time_sec"] if legacy_m else "n/a"),
    ]

    col_w = max(len(r[0]) for r in rows) + 2
    print("\n" + "=" * 70)
    print("CONFRONTO SIMULAZIONI — blocking 100 tick / 5 agenti / Ollama")
    print("=" * 70)
    print(f"{'Metrica':<{col_w}} {'Nuovo (snello)':>20} {'Legacy':>20}")
    print("-" * 70)
    for label, new_v, leg_v in rows:
        print(f"{label:<{col_w}} {str(new_v):>20} {str(leg_v):>20}")
    print("=" * 70)

    if legacy_m:
        speed_ratio = legacy_m["real_time_sec"] / max(new_m["real_time_sec"], 0.01)
        print(f"\nTempo: nuovo progetto {'piu veloce' if speed_ratio > 1 else 'piu lento'} "
              f"di {abs(speed_ratio):.1f}x rispetto al legacy")
        dlg_new = new_m["dialogues"]
        dlg_leg = legacy_m["dialogues"]
        if dlg_leg:
            print(f"Dialoghi: nuovo {dlg_new} vs legacy {dlg_leg} "
                  f"({100*dlg_new/max(dlg_leg,1):.0f}% del legacy)")


def run_legacy(ticks: int, agents: int) -> Path | None:
    script = LEGACY_ROOT / "scripts" / "test_simulation_200_epochs_plan_to_poi.py"
    if not script.exists():
        print(f"Legacy script not found: {script}")
        return None

    env = os.environ.copy()
    env.setdefault("GEN_AGENT_ENABLE_STANFORD_WORKER", "1")
    env.setdefault("GEN_AGENT_DIALOGUE_TIMEOUT", "180")
    model = os.getenv("OLLAMA_MODEL", "gemma4:12b")
    env["OLLAMA_MODEL"] = model

    cmd = [
        sys.executable, str(script),
        "--preset", "blocking_balanced",
        "--ticks", str(ticks),
        "--agents", str(agents),
        "--agent-names", "Marco,Lucia,Giovanni,Anna,Elena",
    ]
    print(f"\n=== Running LEGACY simulation ===")
    print(" ".join(cmd))
    print(f"Model: {model}  (this may take several minutes with blocking Ollama)\n")

    t0 = time.perf_counter()
    result = subprocess.run(cmd, cwd=str(LEGACY_ROOT), env=env)
    elapsed = time.perf_counter() - t0
    print(f"\nLegacy finished in {elapsed:.1f}s (exit={result.returncode})")

    report = find_latest_legacy_report()
    if report:
        print(f"Legacy report: {report}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-legacy", action="store_true")
    parser.add_argument("--skip-new", action="store_true")
    parser.add_argument("--ticks", type=int, default=100)
    parser.add_argument("--agents", type=int, default=5)
    args = parser.parse_args()

    new_m = None
    if not args.skip_new:
        if not NEW_REPORT.exists():
            print(f"New report not found at {NEW_REPORT}")
            print("Run first: python scripts/run_sim_100_ticks_blocking.py --llm ollama")
            return 1
        new_m = extract_new_metrics(load_json(NEW_REPORT) or {})

    legacy_m = None
    if not args.skip_legacy:
        legacy_path = run_legacy(args.ticks, args.agents)
        if legacy_path:
            legacy_m = extract_legacy_metrics(load_json(legacy_path) or {})

    if new_m:
        print_comparison(new_m, legacy_m)
    elif legacy_m:
        print_comparison({"project": "n/a", "preset": "n/a", "agents": 0, "ticks": 0,
                          "block_on_dialogue": True, "ollama_model": "n/a",
                          "interactions": 0, "dialogues": 0, "dialogue_utterances": 0,
                          "missions_completed": 0, "memories_total": 0, "real_time_sec": 0},
                         legacy_m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
