"""
Protocollo stabile per il layer memoria di Gen_Agent.

Tutti i componenti che vogliono leggere/scrivere memorie devono
dipendere da questa interfaccia, mai dall'implementazione concreta.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol, runtime_checkable


@dataclass
class MemoryQuery:
    agent_id: str
    query_text: str
    top_k: int = 5
    memory_types: List[str] = field(default_factory=lambda: ["observation", "reflection", "plan", "social"])
    min_importance: float = 0.0
    scope: str = ""   # "social" = prefer social/chat memories; "sim" = prefer observation/plan


@dataclass
class MemoryRecord:
    memory_id: str
    agent_id: str
    content: str
    memory_type: str
    importance: float
    created_at: float
    last_accessed: float
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class MemoryProtocol(Protocol):
    def store(
        self,
        agent_id: str,
        content: str,
        memory_type: str,
        importance: float,
        **kwargs: Any,
    ) -> str:
        """Salva una memoria. Ritorna l'ID assegnato."""
        ...

    def retrieve(self, query: MemoryQuery) -> List[MemoryRecord]:
        """Recupera memorie rilevanti per la query."""
        ...

    def touch(self, memory_id: str) -> None:
        """Aggiorna il timestamp di ultimo accesso."""
        ...

    def delete(self, memory_id: str) -> None:
        """Rimuove una memoria per ID."""
        ...
