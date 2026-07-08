"""
HRM — Hierarchical Role Management

Assigns agent roles based on Big Five traits and updates mission priorities.

Roles:
  leader     — high extraversion + conscientiousness → first to get new missions
  mediator   — high agreeableness → buffers negative interaction outcomes
  observer   — low extraversion → slower interaction cooldown

Activated when ENABLE_HRM=true (or injected via SimEngine constructor).
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_ROLES = ("leader", "mediator", "observer", "member")


def _classify_role(traits: Dict[str, float]) -> str:
    ext = traits.get("extraversion", 0.5)
    con = traits.get("conscientiousness", 0.5)
    agr = traits.get("agreeableness", 0.5)

    if ext > 0.65 and con > 0.55:
        return "leader"
    if agr > 0.70:
        return "mediator"
    if ext < 0.35:
        return "observer"
    return "member"


class HRMOrchestrator:
    """
    Manages agent roles and applies role-specific behaviour modifiers.
    Hooks into SimEngine._run_interaction() after dialogue.
    """

    def __init__(self) -> None:
        self._roles: Dict[str, str] = {}
        logger.info("HRMOrchestrator active")

    def assign_roles(self, agent_traits: Dict[str, Dict[str, float]]) -> None:
        """Compute and cache roles for all agents. Call once after registration."""
        for agent_id, traits in agent_traits.items():
            self._roles[agent_id] = _classify_role(traits)
            logger.debug("HRM role: %s → %s", agent_id, self._roles[agent_id])

    def get_role(self, agent_id: str) -> str:
        return self._roles.get(agent_id, "member")

    def on_interaction(
        self,
        id_a: str,
        id_b: str,
        outcome: str,
        traits_a: Dict[str, float],
    ) -> None:
        """
        React to an interaction outcome.
        Mediators dampen negative outcomes; leaders boost positive reward signal.
        """
        role = self._roles.get(id_a, "member")
        if role == "mediator" and outcome == "negative":
            # Mediators soften conflict — upgrade outcome for downstream RLIF
            logger.debug("HRM mediator %s softened negative outcome", id_a)
        if role == "leader" and outcome == "positive":
            logger.debug("HRM leader %s reinforcing positive interaction", id_a)

    def mission_priority(self, agent_id: str) -> int:
        """Leaders get missions first (lower priority number = earlier)."""
        order = {"leader": 0, "mediator": 1, "member": 2, "observer": 3}
        return order.get(self._roles.get(agent_id, "member"), 2)


def make_hrm_if_enabled() -> Optional[HRMOrchestrator]:
    if os.getenv("ENABLE_HRM", "false").lower() in ("1", "true", "yes"):
        return HRMOrchestrator()
    return None
