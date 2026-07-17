"""
Central engine factory — wires all optional layers from env flags.

Usage:
    from config.engine_factory import build_sim_engine
    engine, extras = build_sim_engine(scenario)
"""
from __future__ import annotations

import os
import random
import uuid
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gen_agent.interfaces.sim_protocol import AgentConfig
from gen_agent.sim.engine import SimEngine


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Public result types
# ---------------------------------------------------------------------------

@dataclass
class EngineExtras:
    neat_manager: Any = None
    stanford_worker: Any = None
    memory: Any = None


@dataclass
class _CognitionBundle:
    """Internal container — groups all optional cognitive/social layer instances."""
    stanford_adapter: Any = None
    stanford_worker: Any = None
    hrm: Any = None
    rlif: Any = None
    seal: Any = None
    social_learner: Any = None
    game_engine: Any = None
    knowledge_diffusion: Any = None
    neat_manager: Any = None
    biases: Any = None


# ---------------------------------------------------------------------------
# Private builders
# ---------------------------------------------------------------------------

def _build_memory(scenario: Any, llm_prov: Any) -> Any:
    """Build and return a fully configured MemoryManager."""
    from gen_agent.memory.compression.compressor import make_compressor_if_enabled
    from gen_agent.memory.graph.graphrag_retriever import make_graphrag_if_enabled
    from gen_agent.memory.manager import MemoryManager
    from gen_agent.memory.privacy.mars_engine import make_mars_if_enabled
    from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend

    data_dir = os.getenv("GEN_AGENT_DATA_DIR", "data")
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    graphrag = make_graphrag_if_enabled()

    # Dual-mode: PostgreSQL for production, SQLite for local dev
    database_url = os.getenv("DATABASE_URL", "")
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        try:
            from gen_agent.memory.storage.postgres_backend import PostgresMemoryBackend
            backend = PostgresMemoryBackend(database_url)
        except Exception as exc:
            warnings.warn(f"PostgreSQL backend failed ({exc}), falling back to SQLite")
            backend = SQLiteMemoryBackend(str(Path(data_dir) / "central_memory.db"))
    else:
        backend = SQLiteMemoryBackend(str(Path(data_dir) / "central_memory.db"))

    memory = MemoryManager(
        backend=backend,
        graphrag=graphrag,
        mars=make_mars_if_enabled(),
        compressor=make_compressor_if_enabled(),
        data_dir=data_dir,
        llm=llm_prov.complete if scenario.enable_dialogue else None,
        reflection_trigger=int(os.getenv("REFLECTION_TRIGGER", "5")),
        consolidation_interval=int(os.getenv("CONSOLIDATION_INTERVAL", "50")),
    )
    if graphrag is not None:
        graphrag._backend = backend

    if _env_bool("ENABLE_VECTOR_MEMORY"):
        try:
            from gen_agent.memory.vector.faiss_store import attach_vector_store
            attach_vector_store(memory)
        except ImportError:
            pass

    return memory


def _build_cognition(scenario: Any, cfg: Any, memory: Any, llm_prov: Any) -> _CognitionBundle:
    """Build and return all optional cognitive and social layer instances."""
    bundle = _CognitionBundle()

    if _env_bool("ENABLE_STANFORD_WORKER", True):
        from gen_agent.integrations.stanford.adapter import get_stanford_adapter
        from gen_agent.integrations.stanford.worker import StanfordCognitionWorker
        bundle.stanford_adapter = get_stanford_adapter(llm=llm_prov.complete)
        bundle.stanford_worker = StanfordCognitionWorker(
            adapter=bundle.stanford_adapter,
            world=scenario.world,
            memory_store=memory,
        )

    if _env_bool("ENABLE_HRM"):
        from gen_agent.cognitive.hrm import HRMOrchestrator
        bundle.hrm = HRMOrchestrator()

    if _env_bool("ENABLE_RLIF"):
        from gen_agent.cognitive.rlif import RLIFEngine
        bundle.rlif = RLIFEngine(base_radius=cfg.interaction_radius, base_gap=cfg.min_gap_ticks)

    if _env_bool("ENABLE_SEAL"):
        from gen_agent.cognitive.seal import SEALEnhancer
        bundle.seal = SEALEnhancer()

    if _env_bool("ENABLE_SOCIAL_LEARNING"):
        from gen_agent.cognitive.evolutionary import SocialLearner
        from gen_agent.social.social_learning import make_knowledge_diffusion_if_enabled
        bundle.social_learner = SocialLearner(rlif=bundle.rlif)
        bundle.knowledge_diffusion = make_knowledge_diffusion_if_enabled(memory)

    if _env_bool("ENABLE_GAME_THEORY"):
        from gen_agent.social.game_theory import GameEngine
        bundle.game_engine = GameEngine()

    if _env_bool("ENABLE_NEAT"):
        try:
            from server.neat_manager import create_neat_manager
            bundle.neat_manager = create_neat_manager(None)  # bound after engine is built
        except Exception:
            pass

    if _env_bool("ENABLE_BIASES"):
        from gen_agent.cognitive.biases import BiasLayer
        bundle.biases = BiasLayer()

    return bundle


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_sim_engine(scenario: Any) -> tuple[SimEngine, EngineExtras]:
    """Wire scenario → SimEngine with all configured layers. Returns (engine, extras)."""
    from gen_agent.dialogue.dialogue_engine import DialogueEngine
    from gen_agent.llm.provider import get_llm_provider
    from gen_agent.sim.missions import MissionSystem

    os.environ.setdefault("LLM_PROVIDER", scenario.llm_provider)
    llm_prov = get_llm_provider(scenario.llm_provider)

    # Wrap with circuit breaker (enabled by default; disable with ENABLE_CIRCUIT_BREAKER=false)
    if _env_bool("ENABLE_CIRCUIT_BREAKER", True) and scenario.llm_provider not in ("mock",):
        from gen_agent.llm.circuit_breaker import CircuitBreaker
        llm_prov = CircuitBreaker(
            llm_prov,
            failure_threshold=int(os.getenv("CB_FAILURE_THRESHOLD", "3")),
            recovery_timeout=float(os.getenv("CB_RECOVERY_TIMEOUT", "30")),
        )

    memory = _build_memory(scenario, llm_prov)
    cog = _build_cognition(scenario, scenario.sim_config, memory, llm_prov)

    dialogue = None
    if scenario.enable_dialogue:
        dialogue = DialogueEngine(
            llm=llm_prov.complete,
            memory_store=memory,
            max_turns=scenario.sim_config.dialogue_max_turns,
            min_words=int(os.getenv("DIALOGUE_MIN_WORDS", "25")),
            max_attempts=int(os.getenv("DIALOGUE_MAX_ATTEMPTS", "2")),
            use_legacy_quality=_env_bool("ENABLE_LEGACY_DIALOGUE_QUALITY", True),
            scenario_description=os.getenv(
                "SCENARIO_DESCRIPTION",
                "A normal day in a small town. Agents meet and chat about everyday life.",
            ),
        )

    cfg = scenario.sim_config
    cfg.missions_enabled = scenario.enable_missions
    missions = None
    if scenario.enable_missions and scenario.world and scenario.world.pois:
        missions = MissionSystem(
            world=scenario.world,
            mission_duration_ticks=cfg.mission_duration_ticks,
        )

    engine = SimEngine(
        config=cfg,
        stanford_adapter=cog.stanford_adapter,
        dialogue_engine=dialogue,
        memory_store=memory,
        world=scenario.world,
        mission_system=missions,
        hrm=cog.hrm,
        rlif=cog.rlif,
        seal=cog.seal,
        social_learner=cog.social_learner,
        game_engine=cog.game_engine,
        knowledge_diffusion=cog.knowledge_diffusion,
        stanford_worker=cog.stanford_worker,
        neat_manager=cog.neat_manager,
        biases=cog.biases,
    )

    # Post-build wiring
    if cog.stanford_worker:
        cog.stanford_worker.bind_engine(engine)
        cog.stanford_worker.start()

    if cog.neat_manager is not None:
        try:
            from server.neat_manager import create_neat_manager
            cog.neat_manager = create_neat_manager(engine)
            engine._neat_manager = cog.neat_manager
            cog.neat_manager.start()
        except Exception:
            pass

    # Agent bootstrap
    rng = random.Random(cfg.seed)
    for name in scenario.agent_names:
        agent_id = str(uuid.uuid4())[:8]
        pos = (
            scenario.world.random_position(rng)
            if scenario.world
            else (rng.uniform(0, 20), rng.uniform(0, 20))
        )
        engine.register_agent(AgentConfig(agent_id=agent_id, name=name, position=pos))
        memory.ensure_agent(agent_id)
        memory.store(
            agent_id=agent_id,
            content=f"{name} joined the simulation.",
            memory_type="observation",
            importance=5.0,
        )
        if cog.stanford_adapter is not None:
            cog.stanford_adapter.register_persona(agent_id, name)

    if cog.hrm:
        cog.hrm.assign_roles({aid: engine._agents[aid].traits for aid in engine._agents})

    if cog.stanford_worker:
        for aid in engine._agents:
            cog.stanford_worker.enqueue_bootstrap(aid, tick=0)

    return engine, EngineExtras(
        neat_manager=cog.neat_manager,
        stanford_worker=cog.stanford_worker,
        memory=memory,
    )
