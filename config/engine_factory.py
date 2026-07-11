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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gen_agent.interfaces.sim_protocol import AgentConfig
from gen_agent.sim.engine import SimEngine


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")


@dataclass
class EngineExtras:
    neat_manager: Any = None
    stanford_worker: Any = None
    memory: Any = None


def build_memory(data_dir: str = "data", llm: Any = None) -> Any:
    from gen_agent.memory.compression.compressor import make_compressor_if_enabled
    from gen_agent.memory.graph.graphrag_retriever import make_graphrag_if_enabled
    from gen_agent.memory.manager import MemoryManager
    from gen_agent.memory.privacy.mars_engine import make_mars_if_enabled
    from gen_agent.memory.storage.sqlite_backend import SQLiteMemoryBackend

    Path(data_dir).mkdir(parents=True, exist_ok=True)
    graphrag = make_graphrag_if_enabled()

    # Dual-mode: PostgreSQL for production, SQLite for local dev
    database_url = os.getenv("DATABASE_URL", "")
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        try:
            from gen_agent.memory.storage.postgres_backend import PostgresMemoryBackend
            backend = PostgresMemoryBackend(database_url)
            central_db = None
        except Exception as exc:
            import warnings
            warnings.warn(f"PostgreSQL backend failed ({exc}), falling back to SQLite")
            central_db = str(Path(data_dir) / "central_memory.db")
            backend = SQLiteMemoryBackend(central_db)
    else:
        central_db = str(Path(data_dir) / "central_memory.db")
        backend = SQLiteMemoryBackend(central_db)

    reflection_trigger = int(os.getenv("REFLECTION_TRIGGER", "5"))
    consolidation_interval = int(os.getenv("CONSOLIDATION_INTERVAL", "50"))

    memory = MemoryManager(
        backend=backend,
        graphrag=graphrag,
        mars=make_mars_if_enabled(),
        compressor=make_compressor_if_enabled(),
        data_dir=data_dir,
        llm=llm,
        reflection_trigger=reflection_trigger,
        consolidation_interval=consolidation_interval,
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


def build_sim_engine(scenario: Any) -> tuple[SimEngine, EngineExtras]:
    from gen_agent.dialogue.dialogue_engine import DialogueEngine
    from gen_agent.llm.provider import get_llm_provider
    from gen_agent.sim.missions import MissionSystem

    os.environ.setdefault("LLM_PROVIDER", scenario.llm_provider)
    llm_prov = get_llm_provider(scenario.llm_provider)
    data_dir = os.getenv("GEN_AGENT_DATA_DIR", "data")
    memory = build_memory(data_dir, llm=llm_prov.complete if scenario.enable_dialogue else None)
    extras = EngineExtras(memory=memory)

    min_words = int(os.getenv("DIALOGUE_MIN_WORDS", "25"))
    max_attempts = int(os.getenv("DIALOGUE_MAX_ATTEMPTS", "2"))
    use_legacy_quality = _env_bool("ENABLE_LEGACY_DIALOGUE_QUALITY", True)

    dialogue = None
    if scenario.enable_dialogue:
        dialogue = DialogueEngine(
            llm=llm_prov.complete,
            memory_store=memory,
            max_turns=scenario.sim_config.dialogue_max_turns,
            min_words=min_words,
            max_attempts=max_attempts,
            use_legacy_quality=use_legacy_quality,
            scenario_description=os.getenv(
                "SCENARIO_DESCRIPTION",
                "A normal day in a small town. Agents meet and chat about everyday life.",
            ),
        )

    missions = None
    if scenario.enable_missions and scenario.world and scenario.world.pois:
        missions = MissionSystem(
            world=scenario.world,
            mission_duration_ticks=scenario.sim_config.mission_duration_ticks,
        )

    cfg = scenario.sim_config
    cfg.missions_enabled = scenario.enable_missions

    stanford_adapter = None
    stanford_worker = None
    if _env_bool("ENABLE_STANFORD_WORKER", True):
        from gen_agent.integrations.stanford.adapter import get_stanford_adapter
        from gen_agent.integrations.stanford.worker import StanfordCognitionWorker

        stanford_adapter = get_stanford_adapter(llm=llm_prov.complete)
        stanford_worker = StanfordCognitionWorker(
            adapter=stanford_adapter,
            world=scenario.world,
            memory_store=memory,
        )
        extras.stanford_worker = stanford_worker

    hrm = rlif = seal = social_learner = game_engine = knowledge_diffusion = None
    if _env_bool("ENABLE_HRM"):
        from gen_agent.cognitive.hrm import HRMOrchestrator
        hrm = HRMOrchestrator()
    if _env_bool("ENABLE_RLIF"):
        from gen_agent.cognitive.rlif import RLIFEngine
        rlif = RLIFEngine(base_radius=cfg.interaction_radius, base_gap=cfg.min_gap_ticks)
    if _env_bool("ENABLE_SEAL"):
        from gen_agent.cognitive.seal import SEALEnhancer
        seal = SEALEnhancer()
    if _env_bool("ENABLE_SOCIAL_LEARNING"):
        from gen_agent.cognitive.evolutionary import SocialLearner
        from gen_agent.social.social_learning import make_knowledge_diffusion_if_enabled
        social_learner = SocialLearner(rlif=rlif)
        knowledge_diffusion = make_knowledge_diffusion_if_enabled(memory)
    if _env_bool("ENABLE_GAME_THEORY"):
        from gen_agent.social.game_theory import GameEngine
        game_engine = GameEngine()

    neat_manager = None
    if _env_bool("ENABLE_NEAT"):
        try:
            from server.neat_manager import create_neat_manager
            neat_manager = create_neat_manager(None)  # bound after engine built
        except Exception:
            neat_manager = None

    engine = SimEngine(
        config=cfg,
        stanford_adapter=stanford_adapter,
        dialogue_engine=dialogue,
        memory_store=memory,
        world=scenario.world,
        mission_system=missions,
        hrm=hrm,
        rlif=rlif,
        seal=seal,
        social_learner=social_learner,
        game_engine=game_engine,
        knowledge_diffusion=knowledge_diffusion,
        stanford_worker=stanford_worker,
        neat_manager=neat_manager,
    )

    if stanford_worker:
        stanford_worker.bind_engine(engine)
        stanford_worker.start()

    if neat_manager is not None:
        try:
            from server.neat_manager import create_neat_manager
            neat_manager = create_neat_manager(engine)
            engine._neat_manager = neat_manager
            extras.neat_manager = neat_manager
            neat_manager.start()
        except Exception:
            pass

    rng = random.Random(cfg.seed)
    for name in scenario.agent_names:
        agent_id = str(uuid.uuid4())[:8]
        pos = scenario.world.random_position(rng) if scenario.world else (
            rng.uniform(0, 20), rng.uniform(0, 20)
        )
        engine.register_agent(AgentConfig(agent_id=agent_id, name=name, position=pos))
        memory.ensure_agent(agent_id)
        memory.store(
            agent_id=agent_id,
            content=f"{name} joined the simulation.",
            memory_type="observation",
            importance=5.0,
        )
        if stanford_adapter is not None:
            stanford_adapter.register_persona(agent_id, name)

    if hrm:
        hrm.assign_roles({aid: engine._agents[aid].traits for aid in engine._agents})

    if stanford_worker:
        for aid in engine._agents:
            stanford_worker.enqueue_bootstrap(aid, tick=0)

    return engine, extras
