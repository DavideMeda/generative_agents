"""
Stanford cognitive bridge — slim port from Gen_Agent legacy stanford_cognitive.py.

Provides an AssociativeMemory-like interface that wraps the project's own
MemoryManager, so the StanfordAdapter can interact with memories without
importing reverie directly.

Rule: only gen_agent/integrations/stanford/ may import reverie/.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class AssociativeMemoryBridge:
    """
    Mimics enough of reverie's AssociativeMemory interface to allow the
    StanfordAdapter to work without the full reverie dependency.

    Backed by the project's MemoryManager per agent.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        memory_store: Any,  # MemoryProtocol
        llm: Callable[[str], str] | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._agent_name = agent_name
        self._memory = memory_store
        self._llm = llm
        self._scratch: dict[str, Any] = {
            "name": agent_name,
            "curr_time": None,
            "curr_tile": None,
            "daily_plan": [],
        }

    # ------------------------------------------------------------------
    # Scratch interface (used by worker/plan logic)
    # ------------------------------------------------------------------

    def get_scratch(self) -> dict[str, Any]:
        return dict(self._scratch)

    def set_scratch(self, key: str, value: Any) -> None:
        self._scratch[key] = value

    def update_scratch(self, updates: dict[str, Any]) -> None:
        self._scratch.update(updates)

    # ------------------------------------------------------------------
    # Memory interface
    # ------------------------------------------------------------------

    def add_memory(
        self,
        content: str,
        memory_type: str = "observation",
        importance: float = 5.0,
    ) -> str:
        return str(self._memory.store(
            agent_id=self._agent_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
        ))

    def retrieve_memories(self, query: str, top_k: int = 5) -> list[str]:
        from gen_agent.interfaces.memory_protocol import MemoryQuery
        try:
            records = self._memory.retrieve(
                MemoryQuery(agent_id=self._agent_id, query_text=query, top_k=top_k)
            )
            return [r.content for r in records]
        except Exception as exc:
            logger.warning("Memory retrieve failed for %s: %s", self._agent_id, exc)
            return []

    # ------------------------------------------------------------------
    # Planning interface
    # ------------------------------------------------------------------

    def generate_daily_plan(self, context: dict[str, Any]) -> list[str]:
        """Generate a structured daily plan using the Stanford structured planner."""
        from gen_agent.integrations.stanford.structured_planner import generate_structured_plan
        if self._llm is None:
            return ["Explore the town", "Meet a neighbor", "Rest at home"]
        try:
            plan = generate_structured_plan(
                llm=self._llm,
                agent_name=self._agent_name,
                memories=self.retrieve_memories("daily routine", top_k=3),
                tick=int(context.get("tick", 0)),
                location=context.get("location", "town"),
            )
            return list(plan.get("steps", []))
        except Exception as exc:
            logger.warning("Plan generation failed for %s: %s", self._agent_id, exc)
            return ["Explore the environment"]

    def run_reflection(self) -> str:
        """Generate a reflection and store it as a memory."""
        from gen_agent.interfaces.memory_protocol import MemoryQuery
        from gen_agent.memory.reflection import generate_reflection
        try:
            records = self._memory.retrieve(
                MemoryQuery(agent_id=self._agent_id, query_text="", top_k=5,
                            memory_types=["observation", "social"])
            )
            text = generate_reflection(
                agent_id=self._agent_id,
                agent_name=self._agent_name,
                memories=records,
                llm=self._llm,
            )
            if text:
                self._memory.store(
                    agent_id=self._agent_id,
                    content=text,
                    memory_type="reflection",
                    importance=6.0,
                )
            return text
        except Exception as exc:
            logger.warning("Reflection failed for %s: %s", self._agent_id, exc)
            return ""


class StanfordCognitionBridge:
    """
    Registry of AssociativeMemoryBridge instances, one per agent.
    Used by engine_factory to bootstrap Stanford cognitive integration.
    """

    def __init__(
        self,
        memory_store: Any,
        llm: Callable[[str], str] | None = None,
    ) -> None:
        self._memory = memory_store
        self._llm = llm
        self._personas: dict[str, AssociativeMemoryBridge] = {}

    def register_agent(self, agent_id: str, name: str) -> AssociativeMemoryBridge:
        if agent_id not in self._personas:
            self._personas[agent_id] = AssociativeMemoryBridge(
                agent_id=agent_id,
                agent_name=name,
                memory_store=self._memory,
                llm=self._llm,
            )
        return self._personas[agent_id]

    def get_persona(self, agent_id: str) -> AssociativeMemoryBridge | None:
        return self._personas.get(agent_id)

    def tick_all(self, tick: int) -> None:
        """Optionally run periodic cognitive tasks per tick (e.g., every 25 ticks)."""
        if tick % 25 != 0:
            return
        for agent_id, persona in self._personas.items():
            try:
                persona.run_reflection()
            except Exception as exc:
                logger.debug("Cognitive tick failed for %s: %s", agent_id, exc)
