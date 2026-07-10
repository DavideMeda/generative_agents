# Modularity Architecture

## Layer Dependency Graph

```
scripts/run_sim_100_ticks_blocking.py
config/launch_profile.py
        │
        ▼
config/engine_factory.py  ◄─── single wiring point for all optional layers
        │
        ├── gen_agent/sim/engine.py          (SimEngine)
        │       ├── gen_agent/sim/missions.py
        │       ├── gen_agent/sim/proximity.py
        │       └── gen_agent/agents/emotions.py
        │
        ├── gen_agent/dialogue/
        │       ├── dialogue_engine.py       (DialogueEngine)
        │       ├── intent_pack.py           (Big Five → intent)
        │       ├── ollama_manager.py        (prompt builder + output validation)
        │       ├── dialogue_guards.py       (meta/identity/language gate)
        │       └── quality_legacy.py        (CORE-light score)
        │
        ├── gen_agent/memory/
        │       ├── manager.py               (MemoryManager + reflection triggers)
        │       ├── reflection.py            (LLM-based reflection generator)
        │       ├── storage/
        │       │   ├── sqlite_backend.py    (local dev)
        │       │   └── postgres_backend.py  (prod / Docker)
        │       ├── graph/graphrag_retriever.py
        │       ├── privacy/mars_engine.py
        │       └── compression/compressor.py
        │
        ├── gen_agent/integrations/stanford/
        │       ├── adapter.py               (StanfordAdapter)
        │       ├── worker.py                (background cognition worker)
        │       ├── cognitive.py             (AssociativeMemoryBridge + registry)
        │       ├── plan_to_poi.py           (plan text → POI target)
        │       └── structured_planner.py    (LLM daily plan generator)
        │
        ├── gen_agent/cognitive/             (HRM, RLIF, SEAL, SocialLearner)
        ├── gen_agent/social/               (GameEngine, KnowledgeDiffusion)
        ├── gen_agent/training/neat/         (NEAT modules)
        └── server/                          (FastAPI router, NEAT manager, state)
```

## Boundary Rule: `reverie/`

Only `gen_agent/integrations/stanford/` may import from `reverie/`.
All other modules must go through `StanfordAdapter` or `AssociativeMemoryBridge`.

## Optional Layers

All optional layers are disabled by default and enabled via env flags:

| Layer | Flag | Module |
|-------|------|--------|
| Stanford worker | `ENABLE_STANFORD_WORKER=1` | `gen_agent/integrations/stanford/worker.py` |
| NEAT | `ENABLE_NEAT=1` | `gen_agent/training/neat/` |
| HRM | `ENABLE_HRM=1` | `gen_agent/cognitive/hrm.py` |
| RLIF | `ENABLE_RLIF=1` | `gen_agent/cognitive/rlif.py` |
| SEAL | `ENABLE_SEAL=1` | `gen_agent/cognitive/seal.py` |
| Game Theory | `ENABLE_GAME_THEORY=1` | `gen_agent/social/game_theory.py` |
| Social Learning | `ENABLE_SOCIAL_LEARNING=1` | `gen_agent/social/social_learning.py` |
| Vector Memory | `ENABLE_VECTOR_MEMORY=1` | `gen_agent/memory/vector/faiss_store.py` |
| GraphRAG | `ENABLE_GRAPHRAG=1` | `gen_agent/memory/graph/graphrag_retriever.py` |

## Adding a New Layer

1. Implement the layer in its own module under the appropriate package.
2. Add a `make_X_if_enabled()` factory function.
3. Wire it in `config/engine_factory.py` behind an `_env_bool("ENABLE_X")` check.
4. Inject it into `SimEngine.__init__()` as an optional parameter.
5. Add the env flag to `.env.example` and `config/launch_profile.py`.
