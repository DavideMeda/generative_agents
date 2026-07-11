"""
MaRS Engine — Memory Access / Retention / Sharing

Controls which memories can be:
  - Shared between agents (diffusion gate)
  - Retained past their natural decay (importance floor)
  - Forced to decay faster (privacy enforcement)

Rules are configured per memory classification:
  public     → shareable, normal retention
  restricted → shareable only within same group (future), slower decay
  private    → NOT shareable, boosted decay (faster forgetting)

Activated when ENABLE_MARS=true.
"""
from __future__ import annotations

import logging
import os

from gen_agent.memory.privacy.classifier import classify

logger = logging.getLogger(__name__)

_POLICIES = {
    "public":     {"shareable": True,  "decay_multiplier": 1.0,  "importance_floor": 0.0},
    "restricted": {"shareable": False, "decay_multiplier": 0.8,  "importance_floor": 2.0},
    "private":    {"shareable": False, "decay_multiplier": 1.5,  "importance_floor": 0.0},
}


class MaRSEngine:
    """
    Intercepts memory operations to enforce privacy policies.
    Inject into MemoryManager as a filter layer.
    """

    def __init__(self) -> None:
        logger.info("MaRSEngine active")

    def can_share(self, content: str) -> bool:
        classification = classify(content)
        return _POLICIES[classification]["shareable"]

    def decay_multiplier(self, content: str) -> float:
        return _POLICIES[classify(content)]["decay_multiplier"]

    def importance_floor(self, content: str) -> float:
        return _POLICIES[classify(content)]["importance_floor"]

    def apply_to_importance(self, content: str, importance: float) -> float:
        """Ensure importance is at least the policy floor."""
        return max(importance, self.importance_floor(content))

    def classification(self, content: str) -> str:
        return classify(content)


def make_mars_if_enabled() -> MaRSEngine | None:
    if os.getenv("ENABLE_MARS", "false").lower() in ("1", "true", "yes"):
        return MaRSEngine()
    return None
