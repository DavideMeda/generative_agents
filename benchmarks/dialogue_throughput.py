"""
Benchmark: dialogue throughput (stub LLM, nessuna connessione Ollama).

Misura quante conversazioni si completano in N tick quando gli agenti
sono abbastanza vicini da interagire.

Uso:
    python benchmarks/dialogue_throughput.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks._common import make_meta, save_result

TICKS = 50
PRESET = "dialogue_throughput"


def _stub_llm(prompt: str) -> str:
    """LLM stub: risposta minima valida per il dialogue engine."""
    return "Hello there. How are you today? I am doing well, thank you."


def run() -> dict:
    from gen_agent.sim.engine import SimConfig, SimEngine
    from gen_agent.interfaces.sim_protocol import AgentConfig
    from gen_agent.dialogue.dialogue_engine import DialogueEngine

    dialogue = DialogueEngine(llm=_stub_llm, max_turns=2)
    cfg = SimConfig(
        block_on_dialogue=False,
        missions_enabled=False,
        interaction_radius=5.0,
        interaction_every_ticks=1,
        seed=0,
    )
    engine = SimEngine(config=cfg, dialogue_engine=dialogue)
    # 4 agenti molto vicini → massima probabilità di interazione
    for i in range(4):
        engine.register_agent(AgentConfig(
            agent_id=f"agent_{i}",
            name=f"Agent{i}",
            position=(float(i % 2), float(i // 2)),  # griglia 2x2
        ))

    t0 = time.perf_counter()
    total_dialogues = 0
    total_utterances = 0
    for _ in range(TICKS):
        result = engine.advance()
        for ev in result.events:
            if "dialogue" in ev.lower() or "conversation" in ev.lower():
                total_dialogues += 1
    elapsed = time.perf_counter() - t0

    stats = engine.stats()
    result_data = {
        "meta": make_meta(PRESET, model="stub_llm"),
        "ticks": TICKS,
        "n_agents": 4,
        "elapsed_s": round(elapsed, 4),
        "ticks_per_sec": round(TICKS / elapsed, 2),
        "dialogue_events_counted": total_dialogues,
        "engine_stats": stats,
    }
    print(f"[dialogue_throughput] {TICKS} ticks / {elapsed:.3f}s, "
          f"dialogue_events={total_dialogues}")
    return result_data


if __name__ == "__main__":
    save_result(PRESET, run())
