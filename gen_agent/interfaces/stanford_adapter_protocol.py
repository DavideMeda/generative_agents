"""
Protocollo per l'adapter che fa da ponte tra Gen_Agent e il codice Stanford.

Isola il resto del sistema da qualsiasi dipendenza diretta
ai path/moduli della repo Stanford (reverie/, environment/).
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StanfordAdapterProtocol(Protocol):
    def run_agent_plan(self, agent_id: str, context: dict[str, Any]) -> dict[str, Any]:
        """Esegue il ciclo plan/act di un agente Stanford. Ritorna il plan risultante."""
        ...

    def run_reflection(self, agent_id: str, memories: list[str]) -> list[str]:
        """Chiede all'agente Stanford di fare una reflection sulle memorie date."""
        ...

    def get_agent_scratch(self, agent_id: str) -> dict[str, Any]:
        """Legge il scratch pad interno dell'agente Stanford."""
        ...

    def set_agent_scratch(self, agent_id: str, data: dict[str, Any]) -> None:
        """Aggiorna il scratch pad interno dell'agente Stanford."""
        ...
