#!/usr/bin/env python3
"""Print side-by-side comparison: new full run vs legacy sample/extrapolation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW = ROOT / "output" / "sim_blocking_100_new.json"
LEGACY = ROOT / "output" / "sim_blocking_100_legacy.json"


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def extrapolate(legacy: dict, target_ticks: int) -> dict:
    """Scale legacy sample metrics to target_ticks (linear estimate)."""
    done = legacy.get("final_tick", legacy.get("ticks_requested", 1)) or 1
    factor = target_ticks / done
    return {
        "project": f"{legacy.get('project', 'legacy')} [stima x{factor:.1f}]",
        "ticks": target_ticks,
        "agents": legacy.get("agents", 5),
        "interactions": round(legacy.get("interactions", 0) * factor),
        "dialogues": round(legacy.get("dialogues", 0) * factor),
        "dialogue_utterances": round(legacy.get("dialogue_utterances", 0) * factor),
        "missions_completed": legacy.get("missions_completed", 0),
        "memories_total": round(legacy.get("memories_total", 0) * factor),
        "real_time_sec": round(legacy.get("real_time_sec", 0) * factor, 1),
        "ollama_model": legacy.get("ollama_model", "n/a"),
        "preset": legacy.get("scenario", "blocking_balanced"),
        "block_on_dialogue": True,
        "note": f"Estrapolato da {done} tick reali",
    }


def row(label, a, b):
    print(f"{label:<28} {str(a):>22} {str(b):>22}")


def main() -> None:
    new = load(NEW)
    if not new:
        print(f"Manca report nuovo: {NEW}")
        sys.exit(1)

    legacy_raw = load(LEGACY)
    if legacy_raw:
        if legacy_raw.get("final_tick", 0) < 100:
            legacy = extrapolate(legacy_raw, 100)
        else:
            legacy = legacy_raw
    else:
        # Reference blocking_balanced (documented targets, no run file)
        legacy = {
            "project": "Gen_Agent legacy (ref. preset)",
            "ticks": 100,
            "agents": 5,
            "interactions": "~8-15",
            "dialogues": "~5-10",
            "dialogue_utterances": "~20-40",
            "missions_completed": "n/a",
            "memories_total": "~40-80",
            "real_time_sec": "~7200+",
            "ollama_model": new.get("ollama_model"),
            "preset": "blocking_balanced",
            "block_on_dialogue": True,
            "note": "Stima da preset docs (150 tick = 2-4h)",
        }

    nm = {
        "project": new.get("project"),
        "ticks": new.get("final_tick"),
        "agents": new.get("agents"),
        "interactions": new.get("interactions"),
        "dialogues": new.get("dialogues"),
        "dialogue_utterances": new.get("dialogue_utterances"),
        "missions_completed": new.get("missions_completed"),
        "memories_total": new.get("memories_total"),
        "real_time_sec": new.get("real_time_sec"),
        "ollama_model": new.get("ollama_model"),
        "preset": new.get("scenario"),
        "block_on_dialogue": new.get("block_on_dialogue"),
    }
    lm = {k: legacy.get(k, "n/a") for k in nm}

    print("=" * 74)
    print("CONFRONTO — 100 tick | 5 agenti | Ollama bloccante | blocking_balanced-like")
    print("=" * 74)
    row("Metrica", "Nuovo (modulare)", "Legacy")
    print("-" * 74)
    for k in nm:
        row(k, nm[k], lm[k])
    if legacy.get("note"):
        print(f"\nNota legacy: {legacy['note']}")
    print("=" * 74)

  # Architecture delta
    print("\n--- Differenze architetturali (nuovo piu snello) ---")
    deltas = [
        ("Core SimEngine", "~420 righe modulari", "~1500+ righe monolitiche"),
        ("Memoria", "SQLite + layer opt-in", "UniversalMemoryManager ~2300 righe"),
        ("LLM", "Provider astratto (stdlib)", "Accoppiato al worker dialoghi"),
        ("Stanford", "Adapter opzionale", "Worker sempre attivo nei preset"),
        ("Docker/CI", "Multi-stage + compose modulare", "Monolitico vibecoded"),
        ("Layer avanzati", "HRM/RLIF/SEAL via env flag", "Integrati nel core"),
    ]
    for a, b, c in deltas:
        print(f"  {a}: {b} vs {c}")

    rt_new = float(new.get("real_time_sec", 1))
    if isinstance(lm.get("real_time_sec"), (int, float)) and lm["real_time_sec"]:
        ratio = lm["real_time_sec"] / rt_new
        print(f"\nTempo stimato: nuovo ~{rt_new/60:.0f} min vs legacy ~{lm['real_time_sec']/60:.0f} min")


if __name__ == "__main__":
    main()
