"""
Protocollo stabile per il motore di simulazione di Gen_Agent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class AgentConfig:
    agent_id: str
    name: str
    position: tuple[float, float] = (0.0, 0.0)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class TickResult:
    tick: int
    events: list[dict[str, Any]] = field(default_factory=list)
    agent_states: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SimProtocol(Protocol):
    def register_agent(self, config: AgentConfig) -> str:
        """Registra un agente nel motore. Ritorna agent_id."""
        ...

    def advance(self) -> TickResult:
        """Avanza di un tick. Ritorna eventi e stati."""
        ...

    def snapshot(self) -> dict[str, Any]:
        """Ritorna stato corrente dell'intera simulazione."""
        ...

    def reset(self) -> None:
        """Azzera la simulazione (utile per test)."""
        ...
