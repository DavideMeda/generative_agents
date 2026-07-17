#!/usr/bin/env python3
"""
Add a benchmark entry from a simulation report JSON.

Usage:
    python benchmarks/add_entry.py output/sim_blocking_100_v2.json
    python benchmarks/add_entry.py output/sim_blocking_100_v2.json --notes "after FAISS upgrade"
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HISTORY_PATH = Path(__file__).resolve().parent / "history.json"


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a benchmark entry from a simulation report")
    parser.add_argument("report", help="Path to simulation report JSON")
    parser.add_argument("--notes", default="", help="Optional notes for this entry")
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"Error: report file not found: {report_path}", file=sys.stderr)
        sys.exit(1)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    commit = _git_commit()

    entry: dict = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "commit": commit,
        "preset": report.get("scenario", report.get("example", "unknown")),
        "ticks": report.get("ticks_requested", report.get("ticks", 0)),
        "agents": report.get("agents", 0),
        "llm": report.get("llm", report.get("llm_used", "mock")),
        "model": report.get("ollama_model") or report.get("openrouter_model") or report.get("model", "mock"),
        "dialogues": report.get("dialogues", 0),
        "utterances": report.get("dialogue_utterances", 0),
        "memories": report.get("memories_total", 0),
        "reflections": report.get("reflections_generated", 0),
        "real_time_sec": report.get("real_time_sec", 0),
        "avg_sec_per_tick": report.get("avg_sec_per_tick", 0),
    }
    if args.notes:
        entry["notes"] = args.notes

    data: list = []
    if HISTORY_PATH.exists():
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    data.append(entry)
    HISTORY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Added entry [{commit}]: {entry['dialogues']} dialogues, "
          f"{entry['memories']} memories, {entry['real_time_sec']:.1f}s")
    print(f"History: {HISTORY_PATH} ({len(data)} entries total)")


if __name__ == "__main__":
    main()
