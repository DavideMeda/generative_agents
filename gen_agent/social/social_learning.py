"""
[RESEARCH LAYER] Social Learning — imitation and knowledge diffusion.

Status: experimental — not covered by CI tests, excluded from the coverage gate.
Enable: ENABLE_SOCIAL_LEARNING=true

ImitationEngine:
  Every N ticks, agents with lower reward copy a strategy from higher-reward agents.
  (Complements SocialLearner in cognitive/evolutionary.py — this version also
  propagates knowledge through the memory store.)

KnowledgeDiffusion:
  When two agents meet, "public" memories propagate with a probability.
  Simulates gossip, rumours, and shared knowledge formation.

Activated when ENABLE_SOCIAL_LEARNING=true (same flag as SocialLearner).
"""
from __future__ import annotations

import logging
import os
import random
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeDiffusion:
    """
    Spreads public memories between nearby agents on interaction.

    Requires a MemoryProtocol-compatible store.
    """

    def __init__(
        self,
        memory_store: Any = None,
        diffusion_prob: float = 0.3,
        max_memories_per_step: int = 2,
        rng: random.Random | None = None,
    ) -> None:
        self._mem = memory_store
        self._prob = diffusion_prob
        self._max = max_memories_per_step
        self._rng = rng or random.Random()

    def on_interaction(self, id_a: str, id_b: str) -> None:
        """
        Copy up to max_memories_per_step memories from a → b and b → a
        with probability diffusion_prob each.
        """
        if self._mem is None:
            return
        self._diffuse(id_a, id_b)
        self._diffuse(id_b, id_a)

    def _diffuse(self, source_id: str, target_id: str) -> None:
        from gen_agent.interfaces.memory_protocol import MemoryQuery
        try:
            records = self._mem.retrieve(
                MemoryQuery(agent_id=source_id, query_text="", top_k=10)
            )
            public = [r for r in records if getattr(r, "memory_type", "") == "observation"]
            for r in public[: self._max]:
                if self._rng.random() < self._prob:
                    self._mem.store(
                        agent_id=target_id,
                        content=f"[heard from {source_id}] {r.content}",
                        memory_type="hearsay",
                        importance=r.importance * 0.6,
                    )
                    logger.debug("Diffused memory %s → %s", source_id, target_id)
        except Exception as exc:
            logger.debug("KnowledgeDiffusion skipped: %s", exc)


def make_knowledge_diffusion_if_enabled(memory_store: Any = None) -> KnowledgeDiffusion | None:
    if os.getenv("ENABLE_SOCIAL_LEARNING", "false").lower() in ("1", "true", "yes"):
        return KnowledgeDiffusion(memory_store=memory_store)
    return None
