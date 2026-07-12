from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from gen_agent.training.neat.genome import NEATGenome
from gen_agent.training.neat.policy import NEATPolicy


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return float(abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1])))


def _agent_key(agent: Any) -> str:
    return str(getattr(agent, "agent_id", None) or getattr(agent, "name", "agent"))


class NEATEvaluator:
    """Scores genomes against the current simulation state without mutating the engine."""

    def __init__(self, engine: Any, eval_ticks: int = 200, eval_agents: int = 10) -> None:
        self.engine = engine
        self.eval_ticks = max(1, int(eval_ticks))
        self.eval_agents = max(1, int(eval_agents))

    def evaluate(self, genome: NEATGenome, mode: str = "collective") -> float:
        agent_scores = self.evaluate_agents(genome, mode=mode)
        if not agent_scores:
            return 0.0
        return float(np.mean(list(agent_scores.values())))

    def evaluate_agents(self, genome: NEATGenome, mode: str = "collective") -> dict[str, float]:
        agents = list(getattr(self.engine, "agents", []) or [])[: self.eval_agents]
        world = getattr(self.engine, "world", None)
        if not agents or world is None:
            return {}
        policy = NEATPolicy(genome)
        scores: dict[str, float] = {}
        for agent in agents:
            others = [
                o
                for o in agents
                if getattr(o, "agent_id", None) != getattr(agent, "agent_id", None)
            ]
            try:
                action = policy.decide(agent, world, others)
                scores[_agent_key(agent)] = self._score_action(agent, world, others, action, mode)
            except Exception:
                scores[_agent_key(agent)] = 0.0
        return scores

    def _score_action(
        self, agent: Any, world: Any, others: Iterable[Any], action: dict[str, float], mode: str
    ) -> float:
        pos = getattr(agent, "pos", (0, 0))
        stress = float((getattr(agent, "emotions", {}) or {}).get("stress", 0.3))
        valence = float((getattr(agent, "emotions", {}) or {}).get("valence", 0.0))
        social_score = self._social_score(pos, others, action)
        poi_score = self._poi_score(pos, world, action)
        move_score = self._move_score(action)
        emotion_score = max(0.0, min(1.0, (valence + 1.0) / 2.0)) * 0.15
        stress_penalty = max(0.0, min(1.0, stress)) * 0.15
        base = 0.25 * social_score + 0.30 * poi_score + 0.25 * move_score + emotion_score
        if str(mode).lower() in ("emotions", "individual"):
            base = 0.35 * social_score + 0.15 * poi_score + 0.20 * move_score + 0.20 * emotion_score
        return float(max(0.0, min(1.0, base - stress_penalty + 0.10)))

    def _social_score(
        self, pos: tuple[int, int], others: Iterable[Any], action: dict[str, float]
    ) -> float:
        nearest = None
        for other in others:
            d = _dist(pos, getattr(other, "pos", pos))
            nearest = d if nearest is None else min(nearest, d)
        if nearest is None:
            return 0.5
        social_drive = float(action.get("seek_social", 0.0)) + float(action.get("interact", 0.0))
        avoid_drive = float(action.get("avoid_crowd", 0.0))
        if nearest <= 3:
            return max(0.0, min(1.0, social_drive * 0.6 + avoid_drive * 0.4))
        return max(0.0, min(1.0, social_drive * 0.8 + 0.2))

    def _poi_score(self, pos: tuple[int, int], world: Any, action: dict[str, float]) -> float:
        pois = getattr(world, "pois", []) or []
        if not pois:
            return float(action.get("explore", 0.0))
        nearest = None
        for poi in pois:
            try:
                d = _dist(pos, (int(poi.get("x")), int(poi.get("y"))))
                nearest = d if nearest is None else min(nearest, d)
            except Exception:
                continue
        if nearest is None:
            return 0.5
        proximity = 1.0 - max(0.0, min(1.0, nearest / max(1.0, world.width + world.height)))
        return float(max(0.0, min(1.0, 0.6 * float(action.get("seek_poi", 0.0)) + 0.4 * proximity)))

    def _move_score(self, action: dict[str, float]) -> float:
        movement = max(
            float(action.get("move_up", 0.0)),
            float(action.get("move_down", 0.0)),
            float(action.get("move_left", 0.0)),
            float(action.get("move_right", 0.0)),
        )
        stay = float(action.get("stay_put", 0.0))
        explore = float(action.get("explore", 0.0))
        return max(0.0, min(1.0, 0.50 * movement + 0.25 * explore + 0.25 * (1.0 - stay)))
