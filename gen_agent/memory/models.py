"""
Core data models for the Gen_Agent memory system.

These are plain dataclasses — no ORM coupling, no storage details.
Storage backends and retrieval logic live in separate modules.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gen_agent.interfaces.memory_protocol import MemoryRecord


@dataclass
class Memory:
    """A single memory record belonging to one agent."""

    agent_id: str
    content: str
    memory_type: str  # "observation" | "reflection" | "plan"
    importance: float  # 0.0 – 10.0

    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.importance <= 10.0:
            raise ValueError(f"importance must be in [0, 10], got {self.importance}")
        if self.memory_type not in {"observation", "reflection", "plan", "social"}:
            raise ValueError(f"unknown memory_type: {self.memory_type!r}")

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def to_record(self) -> MemoryRecord:
        """Return a MemoryRecord view of this Memory (no copy of heavy fields)."""
        from gen_agent.interfaces.memory_protocol import MemoryRecord  # noqa: PLC0415
        return MemoryRecord(
            memory_id=self.memory_id,
            agent_id=self.agent_id,
            content=self.content,
            memory_type=self.memory_type,
            importance=self.importance,
            created_at=self.created_at,
            last_accessed=self.last_accessed,
            extra=self.extra,
        )


