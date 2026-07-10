"""
Adapter concreto che fa da ponte verso il codice Stanford (reverie/).

Questo è l'UNICO punto del codebase Gen_Agent che può importare da reverie/.
Tutto il resto del sistema parla con StanfordAdapterProtocol.

Strategia di isolamento:
- Tutti gli import Stanford sono racchiusi in try/except per ambienti
  dove il codice Stanford non è presente (es. unit test standalone).
- L'adapter trasforma le chiamate Gen_Agent nei formati Stanford e viceversa.
"""
from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Aggiunge la root del fork a sys.path così reverie/ è importabile
_FORK_ROOT = Path(__file__).resolve().parents[4]
if str(_FORK_ROOT) not in sys.path:
    sys.path.insert(0, str(_FORK_ROOT))

_stanford_available = False
try:
    importlib.import_module("reverie")
    _stanford_available = True
    logger.info("Stanford reverie module found at %s", _FORK_ROOT)
except ModuleNotFoundError:
    logger.warning(
        "Stanford reverie module not found — adapter running in stub mode. "
        "Make sure the fork root contains the reverie/ directory."
    )


class StanfordAdapter:
    """
    Implementazione concreta di StanfordAdapterProtocol.

    In stub mode (Stanford non disponibile) restituisce risposte vuote/
    placeholder senza crashare — utile per test e sviluppo offline.
    """

    def __init__(
        self,
        *,
        stub_mode: bool = not _stanford_available,
        llm: Any = None,
    ) -> None:
        self._stub = stub_mode
        self._llm = llm
        self._persona_registry: Dict[str, Any] = {}
        if not stub_mode:
            self._reverie = importlib.import_module("reverie")

    # ------------------------------------------------------------------
    # Implementazione protocollo
    # ------------------------------------------------------------------

    def register_persona(self, agent_id: str, name: str) -> None:
        self._persona_registry[agent_id] = {"name": name, "scratch": {}}

    def run_agent_plan(self, agent_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        from gen_agent.integrations.stanford.structured_planner import generate_structured_plan

        persona = self._persona_registry.get(agent_id) or {}
        name = persona.get("name", agent_id)
        tick = int(context.get("tick", 0))
        location = str(context.get("location", "town"))
        memories = list(context.get("memories") or [])
        poi_names = list(context.get("poi_names") or [])
        plan = generate_structured_plan(
            self._llm, name, memories, tick, location, poi_names=poi_names or None
        )
        if self._stub:
            logger.debug("plan for %s (stub=%s): %s", agent_id, self._stub, plan.get("plan_text", ""))
        return {"plan": plan.get("plan", []), "action": plan.get("focus", "explore"), "plan_text": plan.get("plan_text", "")}

    def run_reflection(self, agent_id: str, memories: List[str]) -> List[str]:
        if not memories:
            return []
        if self._llm is None:
            return [f"Reflected on {len(memories)} memories."]
        prompt = (
            "Summarize these agent memories in 1-2 short reflective sentences:\n"
            + "\n".join(f"- {m}" for m in memories[:8])
        )
        try:
            text = str(self._llm(prompt)).strip()
            return [text] if text else []
        except Exception as exc:
            logger.error("Stanford run_reflection failed: %s", exc)
            return []

    def get_agent_scratch(self, agent_id: str) -> Dict[str, Any]:
        persona = self._persona_registry.get(agent_id, {})
        return dict(persona.get("scratch") or {})

    def set_agent_scratch(self, agent_id: str, data: Dict[str, Any]) -> None:
        persona = self._persona_registry.setdefault(agent_id, {"name": agent_id, "scratch": {}})
        persona["scratch"].update(data)

    # ------------------------------------------------------------------
    # Helpers interni
    # ------------------------------------------------------------------

    def _get_persona(self, agent_id: str) -> Any:
        return self._persona_registry.get(agent_id)


def get_stanford_adapter(llm: Any = None) -> "StanfordAdapter":
    """Factory — LLM used for structured plans when reverie is absent."""
    return StanfordAdapter(llm=llm)
