"""
SimEngine — tick-based simulation engine for Gen_Agent.

Design principles:
  - Single public method: advance() → TickResult
  - All agent state is held in self._agents (dict, not global)
  - Stanford interaction is delegated to StanfordAdapterProtocol, not called directly
  - Thread-safe: internal lock guards state mutations
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from gen_agent.interfaces.sim_protocol import AgentConfig, SimProtocol, TickResult
from gen_agent.interfaces.stanford_adapter_protocol import StanfordAdapterProtocol
from gen_agent.sim.proximity import ProximityConfig, ProximityDetector

logger = logging.getLogger(__name__)


@dataclass
class _AgentState:
    agent_id: str
    name: str
    position: Tuple[float, float]
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SimConfig:
    tick_interval_sec: float = 1.0
    interaction_radius: float = 2.0
    min_gap_ticks: int = 5
    max_agents: int = 50


class SimEngine:
    """
    Implements SimProtocol.

    Lifecycle:
        engine = SimEngine(config)
        engine.register_agent(AgentConfig(...))
        result = engine.advance()   # call repeatedly
    """

    def __init__(
        self,
        config: SimConfig | None = None,
        stanford_adapter: Optional[StanfordAdapterProtocol] = None,
    ) -> None:
        self._cfg = config or SimConfig()
        self._adapter = stanford_adapter  # None = no Stanford calls
        self._lock = threading.Lock()
        self._tick = 0
        self._agents: Dict[str, _AgentState] = {}
        self._proximity = ProximityDetector(
            ProximityConfig(
                interaction_radius=self._cfg.interaction_radius,
                min_gap_ticks=self._cfg.min_gap_ticks,
            )
        )

    # ------------------------------------------------------------------
    # SimProtocol
    # ------------------------------------------------------------------

    def register_agent(self, config: AgentConfig) -> str:
        with self._lock:
            if len(self._agents) >= self._cfg.max_agents:
                raise RuntimeError(
                    f"Agent limit reached ({self._cfg.max_agents}). "
                    "Increase SimConfig.max_agents."
                )
            self._agents[config.agent_id] = _AgentState(
                agent_id=config.agent_id,
                name=config.name,
                position=config.position,
                extra=config.extra,
            )
            logger.debug("Agent registered: %s (%s)", config.agent_id, config.name)
            return config.agent_id

    def advance(self) -> TickResult:
        with self._lock:
            self._tick += 1
            events: List[Dict[str, Any]] = []

            interaction_pairs = self._detect_interactions()
            for id_a, id_b in interaction_pairs:
                event = self._run_interaction(id_a, id_b)
                if event:
                    events.append(event)

            snapshot = {
                aid: {"position": s.position, "name": s.name}
                for aid, s in self._agents.items()
            }
            logger.debug("Tick %d: %d events", self._tick, len(events))
            return TickResult(tick=self._tick, events=events, agent_states=snapshot)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "tick": self._tick,
                "agents": {
                    aid: {"position": s.position, "name": s.name}
                    for aid, s in self._agents.items()
                },
            }

    def reset(self) -> None:
        with self._lock:
            self._tick = 0
            self._agents.clear()
            self._proximity = ProximityDetector(
                ProximityConfig(
                    interaction_radius=self._cfg.interaction_radius,
                    min_gap_ticks=self._cfg.min_gap_ticks,
                )
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_interactions(self) -> List[Tuple[str, str]]:
        """Return pairs of agents that are in proximity and off cooldown."""
        pairs: List[Tuple[str, str]] = []
        agents = list(self._agents.values())
        for i, a in enumerate(agents):
            for b in agents[i + 1 :]:
                if not self._proximity.within_radius(a.position, b.position):
                    continue
                if not self._proximity.can_interact(a.agent_id, b.agent_id, self._tick):
                    continue
                pairs.append((a.agent_id, b.agent_id))
        return pairs

    def _run_interaction(
        self, id_a: str, id_b: str
    ) -> Optional[Dict[str, Any]]:
        """Execute an interaction between two agents, optionally via Stanford adapter."""
        self._proximity.record_interaction(id_a, id_b, self._tick)

        event: Dict[str, Any] = {
            "type": "interaction",
            "tick": self._tick,
            "agents": [id_a, id_b],
        }

        if self._adapter is not None:
            try:
                a_state = self._agents[id_a]
                context = {
                    "other_agent_id": id_b,
                    "tick": self._tick,
                    "position": a_state.position,
                }
                plan = self._adapter.run_agent_plan(id_a, context)
                event["plan"] = plan
            except Exception as exc:
                logger.warning("Stanford adapter failed for %s: %s", id_a, exc)
                event["adapter_error"] = str(exc)

        return event
