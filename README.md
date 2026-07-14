# New Gen Agent

[![CI](https://github.com/DavideMeda/new-gen-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/DavideMeda/new-gen-agent/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

New Gen Agent — cognitive generative agents in a living town.  
Persistent memory with decay and LLM reflections; cognitive biases and emotions modulate decisions.  
LLM dialogues (blocking or mock), missions, structured plans to POIs, social interactions.  
FastAPI + WebSocket live updates, dual storage (SQLite/PostgreSQL), structured logging, CI/tests ready.

Built on top of [Stanford Generative Agents](https://github.com/joonspk-research/generative_agents):
this repo is a **fork** of it (`upstream`), with the reference implementation vendored under `reverie/`.

## Quick start

```bash
# 1. Install (pyproject.toml is the single source of truth — do NOT use old Stanford deps)
pip install -e ".[dev]"

# 2. Pull the Ollama model
ollama pull llama3.2:3b

# 3. Run a 30-tick simulation
python scripts/run_sim_100_ticks_blocking.py --preset fast --ticks 30 --llm ollama
```

## Reproducibility

| Layer | Deterministic? | Notes |
|-------|----------------|-------|
| Agent movement, proximity, missions | **Yes** | `SimConfig.seed=42` fixes RNG |
| Dialogue text, reflections, plans | **No** | LLM output (Ollama/OpenAI) is stochastic |
| Parity metrics (`core_score`, Plan→POI) | **Indicative** | Re-run may differ; pin model + version |

For comparable runs, record in your report: `OLLAMA_MODEL`, preset, tick count, and
the git commit hash.

## Citation

If you use this project academically, cite this repository and the original paper.
See [CITATION.cff](CITATION.cff) (GitHub / Zenodo compatible).

## Docker

```bash
docker compose -f docker-compose.dev.yml up
# server at http://localhost:8000
```

See [docs/guides/DOCKER.md](docs/guides/DOCKER.md) for production (PostgreSQL) setup.

## Architecture

```
launch_profile → engine_factory → SimEngine
                                 ├── DialogueEngine (intent_pack + traits + emotions)
                                 ├── MemoryManager  (SQLite / PostgreSQL dual-mode)
                                 ├── StanfordWorker (async planning + reflection)
                                 ├── MissionSystem
                                 └── optional layers (HRM, RLIF, NEAT, GameTheory…)
```

Full diagram: [docs/architecture/MODULARITY.md](docs/architecture/MODULARITY.md)

## Presets

| Preset | Ticks | Agents | Notes |
|--------|-------|--------|-------|
| `fast` | 20 | 3 | Offline smoke test |
| `blocking_balanced` | 100 | 5 | Legacy parity target |
| `complex` | 200 | 10 | All layers enabled |

## Quality parity checks

```bash
python scripts/compare_simulations.py --skip-legacy
# → output/parity_report.json
```

Thresholds: `core_score > 0.5`, zero meta/wrong-name/non-English turns,
≥1 reflection/agent/100 ticks.

## Documentation

- [Architecture](docs/architecture/MODULARITY.md)
- [Stanford fork relationship](docs/architecture/UPSTREAM_RELATIONSHIP.md)
- [Docker guide](docs/guides/DOCKER.md)
- [Simulation configuration](docs/guides/CONFIGURATORE_SIMULAZIONE.md)
- [Database schema](docs/database/SCHEMA.md)
- [Developer onboarding](docs/guides/DEVELOPER_ONBOARDING.md)
- [Attribution / third-party notices](NOTICE)

## Tests

```bash
pytest                          # unit tests (coverage gate: core modules ≥55%)
pytest tests/integration/       # integration (requires running server or Postgres)
```

Coverage excludes optional research layers (NEAT, social learning, HRM) — see
`[tool.coverage.run] omit` in `pyproject.toml`.

CI runs lint + unit + Postgres migration + smoke on every PR.
The 100-tick Ollama simulation is **manual/nightly** (too slow for PR CI).
