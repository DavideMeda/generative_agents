"""
Protocol for the adapter that bridges Gen_Agent and the Stanford code.

Isolates the rest of the system from any direct dependency
on Stanford repo paths/modules (reverie/, environment/).
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StanfordAdapterProtocol(Protocol):
    def run_agent_plan(self, agent_id: str, context: dict[str, Any]) -> dict[str, Any]:
        """Run the plan/act cycle for a Stanford agent. Returns the resulting plan."""
        ...

    def run_reflection(self, agent_id: str, memories: list[str]) -> list[str]:
        """Ask the Stanford agent to reflect on the given memories."""
        ...

    def get_agent_scratch(self, agent_id: str) -> dict[str, Any]:
        """Read the internal scratch pad of the Stanford agent."""
        ...

    def set_agent_scratch(self, agent_id: str, data: dict[str, Any]) -> None:
        """Update the internal scratch pad of the Stanford agent."""
        ...
