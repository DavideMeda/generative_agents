"""
StanfordExporter — scrive lo stato della simulazione nel formato
atteso dall'UI Stanford (environment/frontend_server).

Il frontend Django Stanford legge i file:
  storage/{sim_code}/movement/{step}.json   → posizioni agenti
  storage/{sim_code}/environment/{step}.json → stato ambiente
  temp_storage/curr_sim_code.json            → codice simulazione corrente
  temp_storage/curr_step.json                → step corrente

Questo modulo viene chiamato opzionalmente dal TickRunner
(attivo solo se STANFORD_UI_EXPORT=true e STANFORD_UI_DIR è impostato).

Documentazione: docs/guides/STANFORD_UI.md
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Prefisso emoji per pronunciatio (placeholder)
_DEFAULT_PRONUNCIATIO = "🚶"


class StanfordExporter:
    """
    Traduce i TickResult del backend modulare nel formato
    file-based del frontend Stanford.
    """

    def __init__(self, storage_dir: str, sim_code: str = "gen_agent_run") -> None:
        self._root = Path(storage_dir)
        self._sim_code = sim_code
        self._movement_dir = self._root / sim_code / "movement"
        self._env_dir = self._root / sim_code / "environment"
        self._temp_dir = self._root.parent / "temp_storage"
        self._movement_dir.mkdir(parents=True, exist_ok=True)
        self._env_dir.mkdir(parents=True, exist_ok=True)
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    def export_tick(self, tick: int, agents: dict[str, Any]) -> None:
        """
        Scrive il file movement/{tick}.json nel formato Stanford.

        Formato atteso:
        {
          "PersonaName": {
            "movement": [x, y],
            "pronunciatio": "emoji",
            "description": "action description",
            "chat": null
          },
          "<step>": tick
        }
        """
        movement: dict[str, Any] = {}
        env: dict[str, Any] = {}

        for agent_id, state in agents.items():
            name = state.get("name", agent_id)
            pos = state.get("position", [0.0, 0.0])
            # Stanford usa coordinate intere su griglia
            x = int(round(pos[0])) if isinstance(pos, list | tuple) and len(pos) >= 1 else 0
            y = int(round(pos[1])) if isinstance(pos, list | tuple) and len(pos) >= 2 else 0

            target = state.get("target_poi")
            description = f"going to {target}" if target else "exploring"
            state.get("emotion", "")
            pronunciatio = _DEFAULT_PRONUNCIATIO

            movement[name] = {
                "movement": [x, y],
                "pronunciatio": pronunciatio,
                "description": description,
                "chat": None,
            }
            env[name] = {"x": x, "y": y, "description": description}

        movement["<step>"] = tick
        self._write_json(self._movement_dir / f"{tick}.json", movement)
        self._write_json(self._env_dir / f"{tick}.json", env)

        # Aggiorna i file di stato corrente letti da home()
        self._write_json(self._temp_dir / "curr_sim_code.json", {"sim_code": self._sim_code})
        self._write_json(self._temp_dir / "curr_step.json", {"step": tick})
        logger.debug("stanford_exporter.tick_exported", tick=tick, agents=len(agents))

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


_exporter: StanfordExporter | None = None


def get_exporter() -> StanfordExporter | None:
    """
    Restituisce l'exporter se STANFORD_UI_EXPORT=true,
    None altrimenti (esportazione disabilitata).
    """
    global _exporter
    if _exporter is not None:
        return _exporter
    if os.getenv("STANFORD_UI_EXPORT", "false").lower() != "true":
        return None
    ui_dir = os.getenv("STANFORD_UI_DIR", "")
    if not ui_dir:
        logger.warning(
            "stanford_exporter.disabled",
            reason="STANFORD_UI_EXPORT=true but STANFORD_UI_DIR not set",
        )
        return None
    storage_dir = str(Path(ui_dir) / "storage")
    sim_code = os.getenv("STANFORD_SIM_CODE", "gen_agent_run")
    _exporter = StanfordExporter(storage_dir=storage_dir, sim_code=sim_code)
    logger.info(
        "stanford_exporter.enabled",
        storage_dir=storage_dir,
        sim_code=sim_code,
    )
    return _exporter
