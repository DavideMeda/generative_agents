"""
Stable protocol for the Gen_Agent memory layer.

All components that read/write memories must depend on this interface,
never on a concrete implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class MemoryQuery:
    agent_id: str
    query_text: str
    top_k: int = 5
    memory_types: list[str] = field(default_factory=lambda: ["observation", "reflection", "plan", "social"])
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
        """Store a memory. Returns the assigned ID."""
        ...

    def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]:
        """Retrieve memories relevant to the query."""
        ...

    def touch(self, memory_id: str) -> None:
        """Update the last-accessed timestamp."""
        ...

    def delete(self, memory_id: str) -> None:
        """Remove a memory by ID."""
        ...
