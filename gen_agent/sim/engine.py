"""
SimEngine — tick-based simulation engine for Gen_Agent.

Design principles:
  - Single public method: advance() -> TickResult
  - All agent state is held in self._agents (dict, not global)
  - Stanford interaction is delegated via StanfordAdapterProtocol
  - Thread-safe: internal lock guards state mutations
  - Optional layers (World, Emotions, Missions, HRM, RLIF, SEAL) injected via constructor
"""
from __future__ import annotations

import logging
import math
import random
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from gen_agent.interfaces.sim_protocol import AgentConfig, TickResult
from gen_agent.interfaces.stanford_adapter_protocol import StanfordAdapterProtocol
from gen_agent.sim.proximity import ProximityConfig, ProximityDetector

if TYPE_CHECKING:
    from gen_agent.agents.emotions import EmotionState
    from gen_agent.cognitive.hrm import HRMOrchestrator
    from gen_agent.cognitive.rlif import RLIFEngine
    from gen_agent.cognitive.seal import SEALEnhancer
    from gen_agent.cognitive.evolutionary import SocialLearner
    from gen_agent.dialogue.dialogue_engine import DialogueEngine
    from gen_agent.interfaces.memory_protocol import MemoryProtocol
    from gen_agent.sim.missions import Mission, MissionSystem
    from gen_agent.world.poi import POI
    from gen_agent.world.world import World

logger = logging.getLogger(__name__)


@dataclass
class _AgentState:
    agent_id: str
    name: str
    position: Tuple[float, float]
    extra: Dict[str, Any] = field(default_factory=dict)
    target_poi: Optional[Any] = field(default=None, repr=False)   # POI | None
    mission: Optional[Any] = field(default=None, repr=False)       # Mission | None
    emotions: Optional[Any] = field(default=None, repr=False)      # EmotionState | None
    traits: Dict[str, float] = field(default_factory=lambda: {
        "openness": 0.5, "conscientiousness": 0.5,
        "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5,
    })


@dataclass
class SimConfig:
    tick_interval_sec: float = 1.0
    interaction_radius: float = 2.0
    min_gap_ticks: int = 5
    interaction_every_ticks: int = 1
    max_agents: int = 50
    block_on_dialogue: bool = False
    dialogue_max_turns: int = 4
    agent_step_size: float = 0.8        # distance moved per tick toward target
    random_walk_step: float = 0.0       # 0 = pure goal-directed movement
    missions_enabled: bool = True
    mission_duration_ticks: int = 30
    seed: int = 42
    # Optional advanced layer flags (read from env if not set explicitly)
    enable_hrm: bool = False
    enable_rlif: bool = False
    enable_seal: bool = False
    enable_social_learning: bool = False
    enable_game_theory: bool = False
    enable_consensus: bool = False


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
        dialogue_engine: Optional["DialogueEngine"] = None,
        memory_store: Optional["MemoryProtocol"] = None,
        world: Optional["World"] = None,
        mission_system: Optional["MissionSystem"] = None,
        # cognitive layer plugins (all optional)
        hrm: Optional["HRMOrchestrator"] = None,
        rlif: Optional["RLIFEngine"] = None,
        seal: Optional["SEALEnhancer"] = None,
        social_learner: Optional["SocialLearner"] = None,
    ) -> None:
        self._cfg = config or SimConfig()
        self._adapter = stanford_adapter
        self._dialogue = dialogue_engine
        self._memory = memory_store
        self._world = world
        self._missions = mission_system
        self._hrm = hrm
        self._rlif = rlif
        self._seal = seal
        self._social_learner = social_learner
        self._rng = random.Random(self._cfg.seed)
        self._lock = threading.Lock()
        self._tick = 0
        self._agents: Dict[str, _AgentState] = {}
        self._proximity = ProximityDetector(
            ProximityConfig(
                interaction_radius=self._cfg.interaction_radius,
                min_gap_ticks=self._cfg.min_gap_ticks,
            )
        )
        self._stats: Dict[str, Any] = {
            "interactions": 0,
            "dialogues": 0,
            "dialogue_utterances": 0,
            "missions_completed": 0,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_agent(self, config: AgentConfig) -> str:
        with self._lock:
            if len(self._agents) >= self._cfg.max_agents:
                raise RuntimeError(
                    f"Agent limit reached ({self._cfg.max_agents}). "
                    "Increase SimConfig.max_agents."
                )
            from gen_agent.agents.emotions import EmotionState
            state = _AgentState(
                agent_id=config.agent_id,
                name=config.name,
                position=config.position,
                extra=config.extra,
                emotions=EmotionState(),
            )
            # Assign initial POI goal if world is available
            if self._world:
                state.target_poi = self._world.random_poi(self._rng)
            self._agents[config.agent_id] = state
            logger.debug("Agent registered: %s (%s)", config.agent_id, config.name)
            return config.agent_id

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)

    def advance(self) -> TickResult:
        with self._lock:
            self._tick += 1
            events: List[Dict[str, Any]] = []

            self._move_agents()

            if self._missions and self._cfg.missions_enabled:
                self._tick_missions()

            interaction_pairs = self._detect_interactions()
            for id_a, id_b in interaction_pairs:
                event = self._run_interaction(id_a, id_b)
                if event:
                    events.append(event)

            # Social learning tick (every 10 ticks)
            if self._social_learner and self._tick % 10 == 0:
                self._social_learner.tick(list(self._agents.values()))

            snapshot = self._build_snapshot()
            logger.debug("Tick %d: %d events", self._tick, len(events))
            return TickResult(tick=self._tick, events=events, agent_states=snapshot)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {"tick": self._tick, "agents": self._build_snapshot()}

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
    # Movement
    # ------------------------------------------------------------------

    def _move_agents(self) -> None:
        for state in self._agents.values():
            if state.target_poi is not None:
                self._step_toward(state, state.target_poi.x, state.target_poi.y)
                # Arrive check
                dist = math.hypot(
                    state.position[0] - state.target_poi.x,
                    state.position[1] - state.target_poi.y,
                )
                if dist < 0.5:
                    logger.debug("%s arrived at %s", state.name, state.target_poi.name)
                    state.target_poi = None
                    if self._world:
                        state.target_poi = self._world.random_poi(self._rng)
            else:
                # Small random jitter when no target
                step = self._cfg.random_walk_step or 0.2
                dx = self._rng.uniform(-step, step)
                dy = self._rng.uniform(-step, step)
                state.position = (state.position[0] + dx, state.position[1] + dy)

    def _step_toward(self, state: _AgentState, tx: float, ty: float) -> None:
        dx = tx - state.position[0]
        dy = ty - state.position[1]
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return
        step = min(self._cfg.agent_step_size, dist)
        nx = state.position[0] + (dx / dist) * step
        ny = state.position[1] + (dy / dist) * step
        state.position = (nx, ny)

    # ------------------------------------------------------------------
    # Missions
    # ------------------------------------------------------------------

    def _tick_missions(self) -> None:
        for state in self._agents.values():
            if state.mission is None or state.mission.completed:
                m = self._missions.assign(state.agent_id, self._tick)  # type: ignore[union-attr]
                state.mission = m
                if m and m.target_poi:
                    state.target_poi = m.target_poi
            elif state.mission and not state.mission.completed:
                target = state.mission.target_poi
                if target:
                    dist = math.hypot(
                        state.position[0] - target.x,
                        state.position[1] - target.y,
                    )
                    if dist < 1.0:
                        state.mission.completed = True
                        self._stats["missions_completed"] += 1
                        logger.debug("%s completed mission: visit %s", state.name, target.name)
                # Expire old missions
                if self._tick >= state.mission.expires_tick:
                    state.mission.completed = True

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------

    def _detect_interactions(self) -> List[Tuple[str, str]]:
        if self._cfg.interaction_every_ticks > 1 and (
            self._tick % self._cfg.interaction_every_ticks != 0
        ):
            return []
        pairs: List[Tuple[str, str]] = []
        agents = list(self._agents.values())
        for i, a in enumerate(agents):
            for b in agents[i + 1:]:
                if not self._proximity.within_radius(a.position, b.position):
                    continue
                if not self._proximity.can_interact(a.agent_id, b.agent_id, self._tick):
                    continue
                pairs.append((a.agent_id, b.agent_id))
        return pairs

    def _run_interaction(self, id_a: str, id_b: str) -> Optional[Dict[str, Any]]:
        self._proximity.record_interaction(id_a, id_b, self._tick)
        self._stats["interactions"] += 1

        a_state = self._agents[id_a]
        b_state = self._agents[id_b]

        event: Dict[str, Any] = {
            "type": "interaction",
            "tick": self._tick,
            "agents": [id_a, id_b],
            "agent_names": [a_state.name, b_state.name],
        }

        if self._adapter is not None:
            try:
                context = {"other_agent_id": id_b, "tick": self._tick, "position": a_state.position}
                plan = self._adapter.run_agent_plan(id_a, context)
                event["plan"] = plan
            except Exception as exc:
                logger.warning("Stanford adapter failed for %s: %s", id_a, exc)

        if self._dialogue is not None:
            dialogue_event = self._run_blocking_dialogue(id_a, id_b, a_state, b_state)
            if dialogue_event:
                event["dialogue"] = dialogue_event

        # Update emotions after interaction
        outcome = "positive" if self._tick % 3 != 0 else "neutral"
        self._update_emotions(a_state, b_state, outcome)

        # Cognitive layer hooks
        if self._rlif:
            try:
                self._rlif.update(id_a, id_b, outcome)
            except Exception as exc:
                logger.debug("RLIF update failed: %s", exc)
        if self._hrm:
            try:
                self._hrm.on_interaction(id_a, id_b, outcome, a_state.traits)
            except Exception as exc:
                logger.debug("HRM hook failed: %s", exc)
        if self._seal:
            try:
                self._seal.update_traits(id_a, a_state.traits, outcome)
            except Exception as exc:
                logger.debug("SEAL update failed: %s", exc)

        return event

    def _run_blocking_dialogue(
        self,
        id_a: str,
        id_b: str,
        a_state: _AgentState,
        b_state: _AgentState,
    ) -> Optional[Dict[str, Any]]:
        if self._dialogue is None:
            return None

        poi_name = a_state.target_poi.name if a_state.target_poi else "common area"
        context = f"tick={self._tick} location={poi_name}"
        started = time.perf_counter()
        conversation = self._dialogue.run(
            agent_a_id=id_a,
            agent_a_name=a_state.name,
            agent_b_id=id_b,
            agent_b_name=b_state.name,
            context=context,
        )
        elapsed = time.perf_counter() - started

        transcript = conversation.transcript()
        self._stats["dialogues"] += 1
        self._stats["dialogue_utterances"] += len(conversation.utterances)

        if self._memory is not None:
            summary = transcript[:500]
            for agent_id, line in (
                (id_a, f"Talked with {b_state.name} near {poi_name}: {summary}"),
                (id_b, f"Talked with {a_state.name} near {poi_name}: {summary}"),
            ):
                self._memory.store(
                    agent_id=agent_id,
                    content=line,
                    memory_type="observation",
                    importance=6.0,
                    tick=self._tick,
                )

        return {
            "blocking": self._cfg.block_on_dialogue,
            "turns": len(conversation.utterances),
            "elapsed_sec": round(elapsed, 3),
            "transcript_preview": transcript[:200],
        }

    def _update_emotions(
        self,
        a: _AgentState,
        b: _AgentState,
        outcome: str,
    ) -> None:
        try:
            from gen_agent.agents.emotions import update_from_interaction
            if a.emotions is not None:
                b_val = b.emotions.valence if b.emotions else 0.0
                a.emotions = update_from_interaction(a.emotions, b_val, outcome)
            if b.emotions is not None:
                a_val = a.emotions.valence if a.emotions else 0.0
                b.emotions = update_from_interaction(b.emotions, a_val, outcome)
        except Exception as exc:
            logger.debug("Emotion update skipped: %s", exc)

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------

    def _build_snapshot(self) -> Dict[str, Any]:
        result = {}
        for aid, s in self._agents.items():
            entry: Dict[str, Any] = {
                "name": s.name,
                "position": s.position,
            }
            if s.emotions is not None:
                entry["emotions"] = {
                    "valence": round(s.emotions.valence, 3),
                    "arousal": round(s.emotions.arousal, 3),
                    "stress": round(s.emotions.stress, 3),
                }
            if s.mission is not None and not s.mission.completed:
                entry["mission"] = {
                    "type": s.mission.mission_type,
                    "target": s.mission.target_poi.name if s.mission.target_poi else None,
                    "expires_tick": s.mission.expires_tick,
                }
            if s.target_poi is not None:
                entry["target_poi"] = s.target_poi.name
            entry["traits"] = s.traits
            result[aid] = entry
        return result
