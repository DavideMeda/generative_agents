"""
Stable protocol for the Gen_Agent simulation engine.
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
        """Register an agent in the engine. Returns agent_id."""
        ...

    def advance(self) -> TickResult:
        """Advance one tick. Returns events and agent states."""
        ...

    def snapshot(self) -> dict[str, Any]:
        """Return current state of the entire simulation."""
        ...

    def reset(self) -> None:
        """Reset the simulation (useful for tests)."""
        ...
