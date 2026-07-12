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

import math
import random
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

from gen_agent.interfaces.sim_protocol import AgentConfig, TickResult
from gen_agent.interfaces.stanford_adapter_protocol import StanfordAdapterProtocol
from gen_agent.sim.proximity import ProximityConfig, ProximityDetector

if TYPE_CHECKING:
    from gen_agent.cognitive.biases import BiasLayer
    from gen_agent.cognitive.evolutionary import SocialLearner
    from gen_agent.cognitive.hrm import HRMOrchestrator
    from gen_agent.cognitive.rlif import RLIFEngine
    from gen_agent.cognitive.seal import SEALEnhancer
    from gen_agent.dialogue.dialogue_engine import DialogueEngine
    from gen_agent.interfaces.memory_protocol import MemoryProtocol
    from gen_agent.sim.missions import MissionSystem
    from gen_agent.social.game_theory import GameEngine
    from gen_agent.social.social_learning import KnowledgeDiffusion
    from gen_agent.world.world import World

logger = structlog.get_logger(__name__)


@dataclass
class _AgentState:
    agent_id: str
    name: str
    position: tuple[float, float]
    extra: dict[str, Any] = field(default_factory=dict)
    target_poi: Any | None = field(default=None, repr=False)   # POI | None
    mission: Any | None = field(default=None, repr=False)       # Mission | None
    emotions: Any | None = field(default=None, repr=False)      # EmotionState | None
    traits: dict[str, float] = field(default_factory=lambda: {
        "openness": 0.5, "conscientiousness": 0.5,
        "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5,
    })
    # NEAT fields
    neat_enabled: bool = False
    neat_policy: Any | None = field(default=None, repr=False)
    neat_mode: str = "movement"
    neat_last_action: Any | None = field(default=None, repr=False)

    @property
    def pos(self) -> tuple[int, int]:
        """Alias for NEAT evaluator (legacy uses integer grid coords)."""
        return (int(round(self.position[0])), int(round(self.position[1])))


@dataclass
class SimConfig:
    tick_interval_sec: float = 1.0
    interaction_radius: float = 2.0
    min_gap_ticks: int = 5
    interaction_every_ticks: int = 1
    max_agents: int = 50
    block_on_dialogue: bool = False
    dialogue_max_turns: int = 4
    dialogue_wait_timeout_seconds: float = 120.0
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
        stanford_adapter: StanfordAdapterProtocol | None = None,
        dialogue_engine: DialogueEngine | None = None,
        memory_store: MemoryProtocol | None = None,
        world: World | None = None,
        mission_system: MissionSystem | None = None,
        # cognitive layer plugins (all optional)
        hrm: HRMOrchestrator | None = None,
        rlif: RLIFEngine | None = None,
        seal: SEALEnhancer | None = None,
        social_learner: SocialLearner | None = None,
        game_engine: GameEngine | None = None,
        knowledge_diffusion: KnowledgeDiffusion | None = None,
        stanford_worker: Any | None = None,
        neat_manager: Any | None = None,
        biases: BiasLayer | None = None,
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
        self._game_engine = game_engine
        self._knowledge_diffusion = knowledge_diffusion
        self._stanford_worker = stanford_worker
        self._neat_manager = neat_manager
        self._biases = biases
        self._rng = random.Random(self._cfg.seed)
        self._lock = threading.Lock()
        self._tick = 0
        self._agents: dict[str, _AgentState] = {}
        self._proximity = ProximityDetector(
            ProximityConfig(
                interaction_radius=self._cfg.interaction_radius,
                min_gap_ticks=self._cfg.min_gap_ticks,
            )
        )
        self._stats: dict[str, Any] = {
            "interactions": 0,
            "dialogues": 0,
            "dialogue_utterances": 0,
            "missions_completed": 0,
            "plan_goals_extracted": 0,
            "plan_to_poi_matches": 0,
            "plan_goals_matched_to_poi": 0,
            "concrete_goals_used": 0,
        }
        self._stats_lock = threading.Lock()
        self._plan_poi_rr: dict[str, int] = {}

    @property
    def config(self) -> SimConfig:
        return self._cfg

    @property
    def agents(self) -> list[_AgentState]:
        return list(self._agents.values())

    @property
    def world(self) -> World | None:
        return self._world

    # ------------------------------------------------------------------
    # NEAT public API (mirrors legacy SimEngine interface)
    # ------------------------------------------------------------------

    def set_neat_policy_for_all(self, policy_factory: Any, mode: str = "movement") -> None:
        with self._lock:
            for s in self._agents.values():
                try:
                    s.neat_policy = policy_factory(s)
                    s.neat_enabled = True
                    s.neat_mode = mode
                except Exception as exc:
                    logger.debug("NEAT policy set failed for %s: %s", s.agent_id, exc)

    def set_neat_policy_for_agent(self, agent_id: str, policy: Any, mode: str = "movement") -> None:
        with self._lock:
            s = self._agents.get(agent_id)
            if s:
                s.neat_policy = policy
                s.neat_enabled = True
                s.neat_mode = mode

    def disable_neat_for_all(self) -> None:
        with self._lock:
            for s in self._agents.values():
                s.neat_enabled = False
                s.neat_policy = None
                s.neat_mode = "movement"
                s.neat_last_action = None

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

    def stats(self) -> dict[str, Any]:
        with self._lock:
            with self._stats_lock:
                return dict(self._stats)

    def note_plan_poi(self, plan_text: str, matched: str | None = None) -> None:
        """Record plan goal extraction and POI match (safe from worker thread)."""
        from gen_agent.integrations.stanford.plan_to_poi import extract_concrete_goals

        goals = extract_concrete_goals(plan_text or "")
        with self._stats_lock:
            if goals:
                self._stats["plan_goals_extracted"] += len(goals)
            if matched:
                self._stats["plan_to_poi_matches"] += 1
                self._stats["plan_goals_matched_to_poi"] += 1

    def _apply_plan_poi_for_state(self, state: _AgentState, plan_text: str) -> str | None:
        if not self._world or not plan_text:
            return None
        from gen_agent.integrations.stanford.plan_to_poi import apply_plan_to_agent

        idx = self._plan_poi_rr.get(state.agent_id, 0)
        matched = apply_plan_to_agent(
            state, plan_text, self._world, rr_index=idx, allow_fallback=True
        )
        if matched:
            self._plan_poi_rr[state.agent_id] = idx + 1
        self.note_plan_poi(plan_text, matched)
        state.extra["last_plan_tick"] = self._tick
        return matched

    def advance(self) -> TickResult:
        with self._lock:
            self._tick += 1
            events: list[dict[str, Any]] = []

            self._decay_emotions()
            self._contagion_step()
            self._apply_rlif_proximity()
            self._move_agents()

            if self._missions and self._cfg.missions_enabled:
                self._tick_missions()

            if self._memory is not None and hasattr(self._memory, "run_decay_batch"):
                self._memory.run_decay_batch(list(self._agents.keys()), self._tick)
            if self._memory is not None and hasattr(self._memory, "run_consolidation_batch"):
                self._memory.run_consolidation_batch(list(self._agents.keys()), self._tick)
            if self._memory is not None and hasattr(self._memory, "maybe_compress"):
                self._memory.maybe_compress(self._tick, list(self._agents.keys()))

            if self._stanford_worker and self._tick % 20 == 0:
                for aid in self._agents:
                    from gen_agent.integrations.stanford.worker import StanfordCognitionJob
                    self._stanford_worker.enqueue(
                        StanfordCognitionJob(agent_id=aid, tick=self._tick, reason="periodic")
                    )

            interaction_pairs = self._detect_interactions()
            for id_a, id_b in interaction_pairs:
                event = self._run_interaction(id_a, id_b)
                if event:
                    events.append(event)

            # Social learning tick (every 10 ticks)
            if self._social_learner and self._tick % 10 == 0:
                self._social_learner.tick(list(self._agents.values()))

            snapshot = self._build_snapshot()
            logger.debug("engine.tick_advanced", tick=self._tick, events=len(events))
            return TickResult(tick=self._tick, events=events, agent_states=snapshot)

    def snapshot(self) -> dict[str, Any]:
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

    def _decay_emotions(self) -> None:
        for state in self._agents.values():
            if state.emotions is not None:
                state.emotions = state.emotions.decay()

    def _contagion_step(self) -> None:
        """Emotion contagion: nearby agents influence each other's valence."""
        agents = list(self._agents.values())
        for i, a in enumerate(agents):
            if a.emotions is None:
                continue
            neighbors_valence = []
            for b in agents:
                if b is a or b.emotions is None:
                    continue
                dist = math.hypot(a.position[0] - b.position[0], a.position[1] - b.position[1])
                if dist <= self._cfg.interaction_radius * 1.5:
                    neighbors_valence.append(b.emotions.valence)
            if neighbors_valence:
                avg_neighbor_v = sum(neighbors_valence) / len(neighbors_valence)
                # Weak contagion: 5% pull toward neighbor average
                new_valence = a.emotions.valence + 0.05 * (avg_neighbor_v - a.emotions.valence)
                try:
                    from gen_agent.agents.emotions import EmotionState
                    a.emotions = EmotionState(
                        valence=max(-1.0, min(1.0, new_valence)),
                        arousal=a.emotions.arousal,
                        stress=a.emotions.stress,
                    )
                except Exception:
                    pass

    def _apply_rlif_proximity(self) -> None:
        if self._rlif is None:
            return
        # ponytail: use average pair-adjusted radius across active agents
        agents = list(self._agents.keys())
        if len(agents) < 2:
            return
        radii = [
            self._rlif.radius_for(agents[i], agents[j])
            for i in range(len(agents))
            for j in range(i + 1, len(agents))
        ]
        if radii:
            self._proximity.config.interaction_radius = sum(radii) / len(radii)

    def _move_agents(self) -> None:
        for state in self._agents.values():
            # NEAT movement hook (pre-movement)
            if state.neat_enabled and state.neat_policy is not None and state.neat_mode == "movement":
                try:
                    obs = self._build_neat_observation(state)
                    action = state.neat_policy.act(obs)
                    state.neat_last_action = action
                    if action is not None and hasattr(action, "__len__") and len(action) >= 2:
                        dx, dy = float(action[0]), float(action[1])
                        state.position = (state.position[0] + dx, state.position[1] + dy)
                        continue  # NEAT takes over movement
                except Exception as exc:
                    logger.debug("NEAT movement failed for %s: %s", state.agent_id, exc)

            if state.target_poi is not None:
                self._step_toward(state, state.target_poi.x, state.target_poi.y)
                dist = math.hypot(
                    state.position[0] - state.target_poi.x,
                    state.position[1] - state.target_poi.y,
                )
                if dist < 0.5:
                    logger.debug("%s arrived at %s", state.name, state.target_poi.name)
                    state.extra.pop("stanford_plan_poi", None)
                    state.extra.pop("concrete_goal_poi", None)
                    state.target_poi = None
            elif state.extra.get("stanford_plan_poi") is not None:
                plan_poi = state.extra["stanford_plan_poi"]
                state.target_poi = plan_poi
                self._step_toward(state, plan_poi.x, plan_poi.y)
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
                # HRM: log agent mission priority (int, lower = higher priority)
                if self._hrm and hasattr(self._hrm, "mission_priority"):
                    try:
                        _prio = self._hrm.mission_priority(state.agent_id)
                        logger.debug("HRM priority for %s: %d", state.agent_id, _prio)
                    except Exception:
                        pass
                m = self._missions.assign(state.agent_id, self._tick)  # type: ignore[union-attr]
                state.mission = m
                if m and m.target_poi:
                    # Plan→POI override: Stanford plan target takes precedence
                    plan_poi = state.extra.get("stanford_plan_poi")
                    if plan_poi and self._world:
                        state.target_poi = plan_poi
                    else:
                        state.target_poi = m.target_poi
            elif state.mission and not state.mission.completed:
                plan_poi = state.extra.get("stanford_plan_poi")
                if plan_poi is not None:
                    state.target_poi = plan_poi
                    if state.mission.target_poi is not plan_poi:
                        state.mission.target_poi = plan_poi
                target = state.mission.target_poi
                if target:
                    dist = math.hypot(
                        state.position[0] - target.x,
                        state.position[1] - target.y,
                    )
                    if dist < 1.0:
                        state.mission.completed = True
                        with self._stats_lock:
                            self._stats["missions_completed"] += 1
                            plan_poi = state.extra.get("stanford_plan_poi")
                            if plan_poi is not None and (
                                plan_poi is target
                                or getattr(plan_poi, "id", None) == getattr(target, "id", None)
                            ):
                                self._stats["concrete_goals_used"] += 1
                        logger.debug("%s completed mission: visit %s", state.name, target.name)
                        # Intrinsic motivation: reward arrival with small emotion boost
                        if state.emotions is not None:
                            try:
                                from gen_agent.agents.emotions import EmotionState
                                state.emotions = EmotionState(
                                    valence=min(1.0, state.emotions.valence + 0.1),
                                    arousal=min(1.0, state.emotions.arousal + 0.05),
                                    stress=max(0.0, state.emotions.stress - 0.05),
                                )
                            except Exception:
                                pass
                # Expire old missions
                if self._tick >= state.mission.expires_tick:
                    state.mission.completed = True

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------

    def _detect_interactions(self) -> list[tuple[str, str]]:
        if self._cfg.interaction_every_ticks > 1 and (
            self._tick % self._cfg.interaction_every_ticks != 0
        ):
            return []
        pairs: list[tuple[str, str]] = []
        agents = list(self._agents.values())
        for i, a in enumerate(agents):
            for b in agents[i + 1:]:
                if not self._proximity.within_radius(a.position, b.position):
                    continue
                if self._rlif:
                    pair_radius = self._rlif.radius_for(a.agent_id, b.agent_id)
                    dist = math.hypot(a.position[0] - b.position[0], a.position[1] - b.position[1])
                    if dist > pair_radius:
                        continue
                    pair_gap = self._rlif.gap_for(a.agent_id, b.agent_id)
                    if not self._proximity.can_interact(a.agent_id, b.agent_id, self._tick, min_gap=pair_gap):
                        continue
                elif not self._proximity.can_interact(a.agent_id, b.agent_id, self._tick):
                    continue
                # Optional BiasLayer: gates interaction on willingness modifier
                if self._biases is not None:
                    last_tick = self._proximity.last_interaction_tick(a.agent_id, b.agent_id)
                    modifier = self._biases.willingness_modifier(
                        a.agent_id, self._tick, last_tick,
                        recent_events=list(a.extra.get("recent_events", [])),
                    )
                    if self._rng.random() > modifier:
                        continue
                pairs.append((a.agent_id, b.agent_id))
        return pairs

    def _run_interaction(self, id_a: str, id_b: str) -> dict[str, Any] | None:
        self._proximity.record_interaction(id_a, id_b, self._tick)
        self._stats["interactions"] += 1

        a_state = self._agents[id_a]
        b_state = self._agents[id_b]

        event: dict[str, Any] = {
            "type": "interaction",
            "tick": self._tick,
            "agents": [id_a, id_b],
            "agent_names": [a_state.name, b_state.name],
        }

        if self._adapter is not None:
            try:
                recent_plan = (self._tick - int(a_state.extra.get("last_plan_tick", -999))) < 25
                skip_plan_llm = bool(self._stanford_worker and recent_plan)
                memories: list[str] = []
                if self._memory is not None:
                    from gen_agent.interfaces.memory_protocol import MemoryQuery
                    records = self._memory.retrieve(
                        MemoryQuery(agent_id=id_a, query_text="interaction", top_k=4)
                    )
                    memories = [r.content for r in records]
                poi_name = a_state.target_poi.name if a_state.target_poi else "common area"
                context = {
                    "other_agent_id": id_b,
                    "tick": self._tick,
                    "position": a_state.position,
                    "location": poi_name,
                    "memories": memories,
                    "poi_names": [p.name for p in self._world.pois] if self._world else [],
                }
                if not skip_plan_llm:
                    plan = self._adapter.run_agent_plan(id_a, context)
                    event["plan"] = plan
                    if plan.get("plan_text"):
                        self._apply_plan_poi_for_state(a_state, str(plan["plan_text"]))
                elif a_state.extra.get("stanford_plan_poi") is not None:
                    a_state.target_poi = a_state.extra["stanford_plan_poi"]
            except Exception as exc:
                logger.warning("Stanford adapter failed for %s: %s", id_a, exc)

        if self._dialogue is not None:
            dialogue_event = self._run_blocking_dialogue(id_a, id_b, a_state, b_state,
                                                          relationship=event.get("plan", {}).get("relationship"))
            if dialogue_event:
                event["dialogue"] = dialogue_event

        outcome = self._resolve_outcome(id_a, id_b, a_state, b_state)
        self._update_emotions(a_state, b_state, outcome)

        if self._knowledge_diffusion and self._memory is not None:
            try:
                self._knowledge_diffusion.on_interaction(id_a, id_b)
            except Exception as exc:
                logger.debug("Knowledge diffusion failed: %s", exc)

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

    def _resolve_outcome(
        self, id_a: str, id_b: str, a_state: _AgentState, b_state: _AgentState
    ) -> str:
        if self._game_engine is not None:
            try:
                result = self._game_engine.play(
                    id_a, id_b, traits_a=a_state.traits, traits_b=b_state.traits
                )
                return result.outcome
            except Exception as exc:
                logger.debug("Game theory failed: %s", exc)
        return "positive" if self._tick % 3 != 0 else "neutral"

    def _run_blocking_dialogue(
        self,
        id_a: str,
        id_b: str,
        a_state: _AgentState,
        b_state: _AgentState,
        relationship: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if self._dialogue is None:
            return None

        poi_name = a_state.target_poi.name if a_state.target_poi else "town square"
        context = f"tick={self._tick} location={poi_name}"
        known_names = [s.name for s in self._agents.values()]

        # Extract emotions as plain dicts for the dialogue engine
        def _em_dict(s: _AgentState) -> dict[str, float] | None:
            if s.emotions is None:
                return None
            return {
                "valence": getattr(s.emotions, "valence", 0.0),
                "arousal": getattr(s.emotions, "arousal", 0.5),
                "stress": getattr(s.emotions, "stress", 0.3),
            }

        started = time.perf_counter()
        timeout = float(self._cfg.dialogue_wait_timeout_seconds or 0)
        deadline = (started + timeout) if (self._cfg.block_on_dialogue and timeout > 0) else None

        conversation = self._dialogue.run(
            agent_a_id=id_a,
            agent_a_name=a_state.name,
            agent_b_id=id_b,
            agent_b_name=b_state.name,
            context=context,
            known_names=known_names,
            location=poi_name,
            traits_a=a_state.traits,
            traits_b=b_state.traits,
            emotions_a=_em_dict(a_state),
            emotions_b=_em_dict(b_state),
            relationship=relationship,
            deadline=deadline,
        )

        elapsed = time.perf_counter() - started
        transcript = conversation.transcript().strip()
        turns = len(conversation.utterances)
        timed_out = bool(conversation.metadata.get("timed_out"))

        # ponytail: legacy counts dialogue when any content > 10 chars
        if turns == 0 or len(transcript) < 10:
            if timed_out or (deadline and elapsed >= timeout * 0.99):
                logger.warning(
                    "engine.dialogue_timeout",
                    elapsed_s=round(elapsed, 2),
                    agent_a=a_state.name,
                    agent_b=b_state.name,
                    tick=self._tick,
                )
            return None

        if timed_out:
            logger.info(
                "engine.dialogue_partial",
                elapsed_s=round(elapsed, 2),
                agent_a=a_state.name,
                agent_b=b_state.name,
                turns=turns,
                tick=self._tick,
            )

        self._stats["dialogues"] += 1
        self._stats["dialogue_utterances"] += turns

        if self._memory is not None:
            summary = transcript[:500]
            for agent_id, partner_name in ((id_a, b_state.name), (id_b, a_state.name)):
                self._memory.store(
                    agent_id=agent_id,
                    content=f"Conversation with {partner_name} at {poi_name}: {summary}",
                    memory_type="social",
                    importance=6.0,
                    tick=self._tick,
                )

        return {
            "blocking": self._cfg.block_on_dialogue,
            "timed_out": timed_out,
            "turns": turns,
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

        # NEAT emotions hook (post-interaction)
        for state in (a, b):
            if state.neat_enabled and state.neat_policy is not None and state.neat_mode == "emotions":
                try:
                    obs = self._build_neat_observation(state)
                    action = state.neat_policy.act(obs)
                    state.neat_last_action = action
                except Exception as exc:
                    logger.debug("NEAT emotions hook failed for %s: %s", state.agent_id, exc)

    def _build_neat_observation(self, state: _AgentState) -> list[float]:
        """Build the observation vector for NEAT (position + emotions + traits)."""
        em = state.emotions
        return [
            float(state.position[0]) / max(1.0, float(getattr(self._world, "width", 50.0))),
            float(state.position[1]) / max(1.0, float(getattr(self._world, "height", 50.0))),
            float(getattr(em, "valence", 0.0)) if em else 0.0,
            float(getattr(em, "arousal", 0.5)) if em else 0.5,
            float(getattr(em, "stress", 0.3)) if em else 0.3,
            float(state.traits.get("extraversion", 0.5)),
            float(state.traits.get("agreeableness", 0.5)),
        ]

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------

    def _build_snapshot(self) -> dict[str, Any]:
        result = {}
        for aid, s in self._agents.items():
            entry: dict[str, Any] = {
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
            if s.neat_enabled:
                entry["neat"] = {
                    "mode": s.neat_mode,
                    "last_action": list(s.neat_last_action or []),
                }
            result[aid] = entry
        return result
