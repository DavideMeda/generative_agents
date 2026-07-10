#!/usr/bin/env python3
"""
Compare Nuovo Gen_Agent vs legacy Gen_Agent blocking simulations.

Produces a side-by-side table AND a structured parity_report.json
with quality metrics (core_score, plan→poi, memory types, reflection).

Usage:
  python scripts/compare_simulations.py [--report output/sim_blocking_30_en.json]
  python scripts/compare_simulations.py --skip-legacy
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
LEGACY_ROOT = ROOT.parent / "Gen_Agent"

# Acceptance thresholds (from plan)
THRESHOLDS = {
    "core_score_mean_min": 0.50,
    "core_score_min_per_dialogue": 0.30,
    "wrong_addressee_max": 0,
    "meta_comments_max": 0,
    "non_english_max": 0,
    "reflections_per_agent_min": 1.0,        # per 100 ticks
    "plan_to_poi_matches_min": 1,
    "dialogue_utterances_min": 8,            # per 100 ticks
}


def load_json(path: Path) -> Optional[dict]:
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


# ------------------------------------------------------------------
# Quality metric extraction
# ------------------------------------------------------------------

def _score_utterance(text: str) -> float:
    """Lightweight CORE score for a single utterance (no deps)."""
    import string
    stop = {"the","a","an","and","or","but","in","on","at","to","for","of","with","is","are","was",
            "were","i","you","he","she","it","we","they","this","that","not","be","have","has","do"}
    words = re.sub(r"[^\w\s]", " ", (text or "").lower()).split()
    words = [w for w in words if w not in stop and len(w) > 2]
    if len(words) < 5:
        return 0.1
    bigrams = [(words[i], words[i+1]) for i in range(len(words)-1)]
    variety = len(set(bigrams)) / max(len(bigrams), 1)
    length_bonus = min(1.0, len(words) / 20)
    return round(variety * 0.7 + length_bonus * 0.3, 3)


def _detect_issues(text: str, speaker: str, listener: str, known_names: List[str]) -> Dict[str, bool]:
    lower = text.lower()
    meta = bool(re.search(
        r"\b(simulation|language model|llm|as an ai|waking up|woke up|virtual reality|"
        r"i cannot generate|here is a possible|this prompt|npc)\b", lower))
    italian_markers = re.findall(
        r"\b(ciao|sono|davvero|felice|anche|questo|quella|perché|molto|grazie|"
        r"stai|ecco|uscito|confuso|mi sento|siamo|vorrei|posso|devo|ancora)\b", lower)
    non_english = len(italian_markers) >= 2

    wrong_addressee = False
    greeting = re.search(
        r"\b(?:hi|hello|hey|ciao|good\s+morning)\s+([a-z][a-z'-]*)", lower)
    if greeting:
        addressed = greeting.group(1).strip()
        if addressed != listener.lower() and addressed in [n.lower() for n in known_names]:
            wrong_addressee = True

    return {"meta": meta, "non_english": non_english, "wrong_addressee": wrong_addressee}


def compute_dialogue_quality(report: dict) -> Dict[str, Any]:
    log = report.get("dialogue_log", [])
    if not log:
        return {"core_score_mean": 0.0, "core_score_min": 0.0, "per_dialogue": [],
                "meta_count": 0, "non_english_count": 0, "wrong_addressee_count": 0}

    agent_names = report.get("agent_names", [])
    scores, meta_c, ne_c, wa_c = [], 0, 0, 0
    per_dialogue = []
    for entry in log:
        preview = entry.get("preview", "")
        agents = entry.get("agents", ["", ""])
        speaker, listener = (agents[0], agents[1]) if len(agents) >= 2 else ("", "")
        # strip "Speaker: " prefix
        text = re.sub(r"^[^:]+:\s*", "", preview).strip()
        sc = _score_utterance(text)
        issues = _detect_issues(text, speaker, listener, agent_names)
        scores.append(sc)
        if issues["meta"]: meta_c += 1
        if issues["non_english"]: ne_c += 1
        if issues["wrong_addressee"]: wa_c += 1
        per_dialogue.append({"tick": entry.get("tick"), "agents": agents, "score": sc, **issues})

    return {
        "core_score_mean": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "core_score_min": round(min(scores), 3) if scores else 0.0,
        "per_dialogue": per_dialogue,
        "meta_count": meta_c,
        "non_english_count": ne_c,
        "wrong_addressee_count": wa_c,
    }


def check_memory_persistence(data_dir: str = "data") -> Dict[str, Any]:
    """Check if per-agent memory DBs exist from previous run."""
    base = ROOT / data_dir / "agents"
    if not base.exists():
        return {"per_agent_dbs": 0, "agents_found": []}
    dbs = list(base.glob("*/memory.db"))
    return {"per_agent_dbs": len(dbs), "agents_found": [p.parent.name for p in dbs]}


def extract_memory_types(report: dict) -> Dict[str, int]:
    """Best-effort count of memory types from trace files."""
    types: Dict[str, int] = {"observation": 0, "social": 0, "reflection": 0, "plan": 0, "other": 0}
    # Sum from report if present
    for k in list(types.keys()):
        if k in report:
            types[k] = int(report[k])
    return types


def extract_new_quality_metrics(report: dict) -> Dict[str, Any]:
    ticks = report.get("final_tick") or report.get("ticks_requested", 0)
    agents = report.get("agents", 1)
    dq = compute_dialogue_quality(report)
    persistence = check_memory_persistence(os.getenv("GEN_AGENT_DATA_DIR", "data"))
    reflections = report.get("reflections_generated", 0)

    return {
        "project": report.get("project", "Nuovo Gen_Agent"),
        "ticks": ticks,
        "agents": agents,
        "interactions": report.get("interactions", 0),
        "dialogues": report.get("dialogues", 0),
        "dialogue_utterances": report.get("dialogue_utterances", 0),
        "missions_completed": report.get("missions_completed", 0),
        "memories_total": report.get("memories_total", 0),
        "real_time_sec": report.get("real_time_sec", 0),
        "ollama_model": report.get("ollama_model", "n/a"),
        "core_score_mean": dq["core_score_mean"],
        "core_score_min": dq["core_score_min"],
        "meta_count": dq["meta_count"],
        "non_english_count": dq["non_english_count"],
        "wrong_addressee_count": dq["wrong_addressee_count"],
        "reflections_generated": reflections,
        "reflections_per_agent_per_100tick": round(
            reflections / max(agents, 1) / max(ticks, 1) * 100, 2),
        "plan_to_poi_matches": report.get("plan_to_poi_matches", "?"),
        "plan_goals_extracted": report.get("plan_goals_extracted", 0),
        "concrete_goals_used": report.get("concrete_goals_used", 0),
        "plan_to_poi_analysis": report.get("plan_to_poi_analysis", {}),
        "block_on_dialogue": report.get("block_on_dialogue", True),
        "scenario": report.get("scenario", "n/a"),
        "per_agent_memory_dbs": persistence["per_agent_dbs"],
        "memory_types": extract_memory_types(report),
    }


# ------------------------------------------------------------------
# Parity check
# ------------------------------------------------------------------

def check_thresholds(m: Dict[str, Any]) -> Dict[str, bool]:
    ticks = m["ticks"] or 1
    scale = 100 / ticks  # normalize to 100 ticks
    return {
        "core_score_mean_ok": m["core_score_mean"] >= THRESHOLDS["core_score_mean_min"],
        "no_meta_ok": m["meta_count"] <= THRESHOLDS["meta_comments_max"],
        "no_non_english_ok": m["non_english_count"] <= THRESHOLDS["non_english_max"],
        "no_wrong_addressee_ok": m["wrong_addressee_count"] <= THRESHOLDS["wrong_addressee_max"],
        "reflections_ok": m["reflections_per_agent_per_100tick"] >= THRESHOLDS["reflections_per_agent_min"],
        "plan_poi_ok": (m["plan_to_poi_matches"] != "?" and
                        int(m["plan_to_poi_matches"] or 0) >= THRESHOLDS["plan_to_poi_matches_min"]),
        "utterances_ok": (m["dialogue_utterances"] * scale) >= THRESHOLDS["dialogue_utterances_min"],
    }


def generate_parity_report(m: Dict[str, Any], out_path: Path) -> None:
    checks = check_thresholds(m)
    passed = sum(checks.values())
    total = len(checks)
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_report": m,
        "thresholds": THRESHOLDS,
        "checks": checks,
        "passed": passed,
        "total": total,
        "parity_score": f"{passed}/{total}",
        "parity_ok": passed == total,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nParity report saved: {out_path}")


def print_quality_comparison(m: Dict[str, Any]) -> None:
    checks = check_thresholds(m)
    print("\n" + "=" * 65)
    print("QUALITY PARITY CHECK vs legacy blocking_balanced")
    print("=" * 65)
    rows = [
        ("core_score mean", m["core_score_mean"], f">= {THRESHOLDS['core_score_mean_min']}", checks["core_score_mean_ok"]),
        ("meta comments", m["meta_count"], "== 0", checks["no_meta_ok"]),
        ("non-English turns", m["non_english_count"], "== 0", checks["no_non_english_ok"]),
        ("wrong addressee", m["wrong_addressee_count"], "== 0", checks["no_wrong_addressee_ok"]),
        ("reflections/agent/100t", m["reflections_per_agent_per_100tick"], f">= {THRESHOLDS['reflections_per_agent_min']}", checks["reflections_ok"]),
        ("plan-POI matches", m["plan_to_poi_matches"], f">= {THRESHOLDS['plan_to_poi_matches_min']}", checks["plan_poi_ok"]),
        ("utterances (norm 100t)", round(m["dialogue_utterances"] * 100 / max(m["ticks"], 1), 1), f">= {THRESHOLDS['dialogue_utterances_min']}", checks["utterances_ok"]),
        ("per-agent memory DBs", m["per_agent_memory_dbs"], ">= agents", True),
    ]
    for label, val, threshold, ok in rows:
        status = "OK" if ok else "FAIL"
        print(f"  {'[' + status + ']':<8}  {label:<30} {str(val):<10}  (target: {threshold})")
    passed = sum(1 for _, _, _, ok in rows if ok)
    print(f"\n  Result: {passed}/{len(rows)} checks passed")
    print("=" * 65)


def print_quantitative_comparison(
    m: Dict[str, Any],
    legacy: Optional[Dict[str, Any]] = None,
    title: str = "QUANTITATIVE COMPARISON — blocking / 5 agents / Ollama",
) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    if legacy and legacy.get("preset"):
        print(f"  Legacy preset: {legacy['preset']}")
    rows = [
        ("Tick", m["ticks"], legacy["ticks"] if legacy else "n/a"),
        ("Interactions", m["interactions"], legacy.get("interactions", "n/a") if legacy else "n/a"),
        ("Dialogues", m["dialogues"], legacy.get("dialogues", "n/a") if legacy else "n/a"),
        ("Utterances", m["dialogue_utterances"], legacy.get("dialogue_utterances", "n/a") if legacy else "n/a"),
        ("Plan goals extracted", m.get("plan_goals_extracted", "?"),
         legacy.get("plan_goals_extracted", "n/a") if legacy else "n/a"),
        ("Plan-POI matches", m["plan_to_poi_matches"],
         legacy.get("plan_to_poi_matches", "n/a") if legacy else "n/a"),
        ("Concrete goals used", m.get("concrete_goals_used", "n/a"),
         legacy.get("concrete_goals_used", "n/a") if legacy else "n/a"),
        ("Missions done", m["missions_completed"], legacy.get("missions_completed", "n/a") if legacy else "n/a"),
        ("Memories total", m["memories_total"], legacy.get("memories_total", "n/a") if legacy else "n/a"),
        ("Reflections", m.get("reflections_generated", 0), "n/a"),
        ("core_score mean", m["core_score_mean"], "n/a"),
        ("Objective completion %", "n/a",
         legacy.get("objective_completion_pct", "n/a") if legacy else "n/a"),
        ("Time (s)", m["real_time_sec"], legacy.get("real_time_sec", "n/a") if legacy else "n/a"),
        ("Ollama model", m["ollama_model"], legacy.get("ollama_model", "n/a") if legacy else "n/a"),
    ]
    col = 22
    print(f"{'Metric':<{col}} {'Nuovo':>20} {'Legacy':>20}")
    print("-" * 70)
    for label, new_v, leg_v in rows:
        print(f"{label:<{col}} {str(new_v):>20} {str(leg_v):>20}")
    print("=" * 70)


def build_comparison_json(
    nuovo: Dict[str, Any],
    legacy: Optional[Dict[str, Any]],
    *,
    label: str,
    nuovo_source: str,
    legacy_source: Optional[str],
) -> dict:
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "comparison": label,
        "nuovo_source": nuovo_source,
        "legacy_source": legacy_source,
        "nuovo": nuovo,
        "legacy": legacy,
        "delta": _delta_metrics(nuovo, legacy) if legacy else {},
    }


def _delta_metrics(nuovo: Dict[str, Any], legacy: Dict[str, Any]) -> dict:
    def d(key: str, nkey: Optional[str] = None) -> Optional[float]:
        nk = nkey or key
        try:
            a = float(nuovo.get(nk, 0) or 0)
            b = float(legacy.get(key, 0) or 0)
            return round(a - b, 3)
        except (TypeError, ValueError):
            return None

    return {
        "dialogues": d("dialogues"),
        "plan_to_poi_matches": d("plan_to_poi_matches"),
        "real_time_sec": d("real_time_sec"),
        "core_score_mean": d("core_score_mean"),
    }


def extract_legacy_metrics(report: dict) -> dict:
    """Normalize legacy harness JSON (summary/performance/run_config) to flat metrics."""
    summary = report.get("summary", report.get("statistics", report))
    perf = report.get("performance", {})
    run_cfg = report.get("run_config", {})
    ticks = summary.get("total_ticks") or summary.get("planned_ticks") or report.get("planned_ticks", 0)
    runtime = perf.get("runtime_seconds") or report.get("runtime_s") or report.get("real_time_sec", 0)
    plan = report.get("plan_to_poi_analysis", {})
    return {
        "project": "Gen_Agent (legacy)",
        "preset": run_cfg.get("preset", "n/a"),
        "ticks": ticks,
        "agents": len(report.get("agents", {})) or summary.get("agents", 0),
        "interactions": summary.get("total_interactions", summary.get("interactions", 0)),
        "dialogues": summary.get("total_dialogues", summary.get("dialogues", 0)),
        "dialogue_utterances": summary.get("dialogue_utterances", 0),
        "missions_completed": summary.get("concrete_goals_used", summary.get("missions_completed", 0)),
        "memories_total": summary.get("memories_created", summary.get("total_memories", 0)),
        "plan_goals_extracted": summary.get("plan_goals_extracted", 0),
        "plan_to_poi_matches": summary.get("plan_goals_matched_to_poi", 0),
        "concrete_goals_used": summary.get("concrete_goals_used", 0),
        "memory_coverage_pct": summary.get("memory_coverage_pct", 0),
        "objective_completion_pct": summary.get("objective_completion_pct", 0),
        "plan_matching_rate": plan.get("matching_rate", 0),
        "real_time_sec": round(float(runtime), 2),
        "ollama_model": run_cfg.get("ollama_model", report.get("ollama_model", "n/a")),
        "block_on_dialogue": run_cfg.get("block_on_dialogue", None),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="output/sim_blocking_30_en.json",
                        help="Path to Nuovo Gen_Agent sim report JSON")
    parser.add_argument("--legacy-report", help="Path to legacy report JSON (skip auto-find)")
    parser.add_argument("--skip-legacy", action="store_true")
    parser.add_argument("--parity-out", default="output/parity_report.json")
    parser.add_argument("--comparison-out", default="output/comparison_vs_legacy.json",
                        help="Structured side-by-side JSON when --legacy-report is set")
    args = parser.parse_args()

    new_path = ROOT / args.report if not Path(args.report).is_absolute() else Path(args.report)
    new_data = load_json(new_path)
    if not new_data:
        print(f"ERROR: report not found at {new_path}")
        return 1

    m = extract_new_quality_metrics(new_data)
    print_quality_comparison(m)
    generate_parity_report(m, ROOT / args.parity_out)

    # Quantitative vs legacy
    legacy_m = None
    legacy_path = None
    if not args.skip_legacy:
        if args.legacy_report:
            legacy_path = Path(args.legacy_report)
            if not legacy_path.is_absolute():
                legacy_path = ROOT / legacy_path
        if legacy_path and legacy_path.exists():
            legacy_raw = load_json(legacy_path) or {}
            legacy_m = extract_legacy_metrics(legacy_raw)
            title = (
                f"QUANTITATIVE COMPARISON — Nuovo vs legacy "
                f"({legacy_m.get('preset', 'unknown preset')})"
            )
            print_quantitative_comparison(m, legacy_m, title=title)
            out = ROOT / args.comparison_out
            comp = build_comparison_json(
                m, legacy_m,
                label=title,
                nuovo_source=str(new_path),
                legacy_source=str(legacy_path),
            )
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(comp, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"\nComparison JSON saved: {out}")
        elif not args.skip_legacy:
            print("\n(No --legacy-report provided; skipping quantitative legacy table)")

    checks = check_thresholds(m)
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"\nFailed checks: {', '.join(failed)}")
        return 2
    print("\nAll quality parity checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
