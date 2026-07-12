"""
Evolutionary Learning module — social imitation + intrinsic motivation.

SocialLearner:
  Every N ticks, the agent with the lowest cumulative reward copies a trait
  from the agent with the highest reward (meta-learning by imitation).

IntrinsicMotivation:
  Agents earn a bonus reward for visiting POIs they have never been to.
  Encourages exploration over exploitation.

Activated when ENABLE_SOCIAL_LEARNING=true.
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from gen_agent.sim.engine import _AgentState


class SocialLearner:
    """
    Implements behaviour copying every N ticks.
    Requires an RLIFEngine to read reward signals.
    """

    def __init__(self, rlif: Any = None, copy_every: int = 10) -> None:
        self._rlif = rlif
        self._copy_every = copy_every
        self._tick_counter = 0
        logger.info("SocialLearner active (copy_every=%d)", copy_every)

    def tick(self, agents: list[_AgentState]) -> None:
        self._tick_counter += 1
        if self._tick_counter % self._copy_every != 0:
            return
        if len(agents) < 2:
            return

        if self._rlif is not None:
            # Find agent with highest vs lowest total reward
            totals: dict[str, float] = {}
            for a in agents:
                aid = a.agent_id
                totals[aid] = sum(
                    v for (x, y), v in self._rlif._rewards.items() if aid in (x, y)
                )
            best_id = max(totals, key=lambda k: totals[k])
            worst_id = min(totals, key=lambda k: totals[k])
        else:
            # Without RLIF, pick randomly
            import random
            ids = [a.agent_id for a in agents]
            best_id, worst_id = random.sample(ids, 2)

        best = next((a for a in agents if a.agent_id == best_id), None)
        worst = next((a for a in agents if a.agent_id == worst_id), None)
        if best is None or worst is None or best_id == worst_id:
            return

        # Copy one random trait from best → worst
        import random
        trait_key = random.choice(list(best.traits.keys()))
        old_val = worst.traits.get(trait_key, 0.5)
        # Blend: 80% own, 20% best — gradual adoption
        worst.traits[trait_key] = round(old_val * 0.8 + best.traits[trait_key] * 0.2, 4)
        logger.debug(
            "SocialLearner: %s copies %s from %s (%.3f → %.3f)",
            worst_id, trait_key, best_id, old_val, worst.traits[trait_key],
        )


class IntrinsicMotivation:
    """
    Tracks which POIs each agent has visited.
    Returns a bonus reward for first visits.
    """

    def __init__(self, bonus: float = 2.0) -> None:
        self._visited: dict[str, set[str]] = {}
        self._bonus = bonus

    def on_poi_visit(self, agent_id: str, poi_id: str) -> float:
        visited = self._visited.setdefault(agent_id, set())
        if poi_id not in visited:
            visited.add(poi_id)
            logger.debug("IntrinsicMotivation: %s → %s (bonus %.1f)", agent_id, poi_id, self._bonus)
            return self._bonus
        return 0.0


def make_social_learner_if_enabled(rlif: Any = None) -> SocialLearner | None:
    if os.getenv("ENABLE_SOCIAL_LEARNING", "false").lower() in ("1", "true", "yes"):
        return SocialLearner(rlif=rlif)
    return None
