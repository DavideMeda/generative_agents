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

    def __init__(self, *, stub_mode: bool = not _stanford_available) -> None:
        self._stub = stub_mode
        if not stub_mode:
            self._reverie = importlib.import_module("reverie")

    # ------------------------------------------------------------------
    # Implementazione protocollo
    # ------------------------------------------------------------------

    def run_agent_plan(self, agent_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if self._stub:
            logger.debug("stub: run_agent_plan(%s)", agent_id)
            return {"plan": [], "action": "idle"}
        # ponytail: interfaccia minima — espande quando reverie espone API stabile
        try:
            persona = self._get_persona(agent_id)
            if persona is None:
                return {"plan": [], "action": "idle"}
            return {"plan": [], "action": "idle", "persona": str(persona)}
        except Exception as exc:
            logger.error("Stanford run_agent_plan failed: %s", exc)
            return {"plan": [], "action": "idle", "error": str(exc)}

    def run_reflection(self, agent_id: str, memories: List[str]) -> List[str]:
        if self._stub:
            logger.debug("stub: run_reflection(%s, %d memories)", agent_id, len(memories))
            return []
        try:
            persona = self._get_persona(agent_id)
            if persona is None:
                return []
            # Stanford reflection API (placeholder — dipende dalla versione)
            return []
        except Exception as exc:
            logger.error("Stanford run_reflection failed: %s", exc)
            return []

    def get_agent_scratch(self, agent_id: str) -> Dict[str, Any]:
        if self._stub:
            return {}
        try:
            persona = self._get_persona(agent_id)
            if persona is None:
                return {}
            scratch = getattr(persona, "scratch", None)
            if scratch is None:
                return {}
            return vars(scratch) if hasattr(scratch, "__dict__") else {}
        except Exception as exc:
            logger.error("Stanford get_agent_scratch failed: %s", exc)
            return {}

    def set_agent_scratch(self, agent_id: str, data: Dict[str, Any]) -> None:
        if self._stub:
            return
        try:
            persona = self._get_persona(agent_id)
            if persona is None:
                return
            scratch = getattr(persona, "scratch", None)
            if scratch is not None:
                for k, v in data.items():
                    setattr(scratch, k, v)
        except Exception as exc:
            logger.error("Stanford set_agent_scratch failed: %s", exc)

    # ------------------------------------------------------------------
    # Helpers interni
    # ------------------------------------------------------------------

    def _get_persona(self, agent_id: str) -> Any:
        """Recupera l'oggetto Persona Stanford per un agent_id dato."""
        # ponytail: lookup naive per ora — estendi con registry se necessario
        try:
            persona_module = importlib.import_module("reverie.backend_server.persona.persona")
            # Il costruttore richiede name e folder — per ora ritorna None se non in sessione
            return None
        except Exception:
            return None


def get_stanford_adapter() -> "StanfordAdapter":
    """Factory singleton-ish — usa stub_mode automatico."""
    return StanfordAdapter()
