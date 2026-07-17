# New Gen Agent

[![CI](https://github.com/DavideMeda/new-gen-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/DavideMeda/new-gen-agent/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

New Gen Agent — cognitive generative agents in a living town.  
Persistent memory with decay and LLM reflections; cognitive biases and emotions modulate decisions.  
LLM dialogues (blocking or mock), missions, structured plans to POIs, social interactions.  
FastAPI + WebSocket live updates, dual storage (SQLite/PostgreSQL), structured logging, CI/tests ready.

**Site:** [davidemeda.github.io/new-gen-agent](https://davidemeda.github.io/new-gen-agent/)

Built on top of [Stanford Generative Agents](https://github.com/joonspk-research/generative_agents):
this repo is a **fork** of it (`upstream`), with the reference implementation vendored under `reverie/`.

## Quick start

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Offline test — no LLM needed
python examples/hello_world.py

# 3. With Ollama (local LLM)
ollama pull llama3.2:3b
python examples/ollama_simple.py

# 4. With OpenRouter API (free tier)
export OPENROUTER_API_KEY=sk-or-...
python examples/openrouter_api.py
```

See [docs/tutorials/GETTING_STARTED.md](docs/tutorials/GETTING_STARTED.md) for the full step-by-step guide.

## Examples

Ready-to-run scripts in `examples/`:

| Script | LLM | What it shows |
|--------|-----|---------------|
| `hello_world.py` | mock | Minimal simulation — runs in 5 s |
| `ollama_simple.py` | Ollama | Real LLM dialogues, auto-fallback if Ollama is down |
| `openrouter_api.py` | OpenRouter | Cloud API (free tier), auto-fallback if key missing |
| `cognitive_biases.py` | mock | ConfirmationBias, AvailabilityHeuristic, AnchoringBias demo |
| `custom_scenario.py` | mock | Template for your own world and scenario |

## Reproducibility

| Layer | Deterministic? | Notes |
|-------|----------------|-------|
| Agent movement, proximity, missions | **Yes** | `SimConfig.seed=42` fixes RNG |
| Dialogue text, reflections, plans | **No** | LLM output is stochastic |
| Parity metrics (Plan→POI) | **Indicative** | Re-run may differ; pin model + version |

For comparable runs, record: `OLLAMA_MODEL`, preset, tick count, and git commit hash.

## Citation

If you use this project academically, cite this repository and the original paper.
See [CITATION.cff](CITATION.cff) (GitHub / Zenodo compatible).

## Docker

```bash
docker compose up                         # SQLite dev (simplest)
docker compose --profile postgres up      # + PostgreSQL + pgAdmin
```

Open `http://localhost:8000` for the live WebSocket dashboard.

See [docs/guides/DOCKER.md](docs/guides/DOCKER.md) and [docs/guides/WEB_UI.md](docs/guides/WEB_UI.md).

## Architecture

```
launch_profile → engine_factory → SimEngine
                                 ├── DialogueEngine   (intent_pack + traits + emotions)
                                 ├── MemoryManager    (SQLite / PostgreSQL dual-mode)
                                 ├── StanfordWorker   (async planning + reflection)
                                 ├── MissionSystem
                                 ├── CircuitBreaker   (LLM resilience)
                                 └── optional layers  (HRM, RLIF, NEAT, GameTheory…)
```

Full diagram: [docs/architecture/MODULARITY.md](docs/architecture/MODULARITY.md)

## Presets & Scenarios

| Preset | Ticks | Agents | Notes |
|--------|-------|--------|-------|
| `fast` | 20 | 3 | Offline smoke test |
| `blocking_balanced` | 100 | 5 | Legacy parity target |
| `complex` | 200 | 10 | All layers enabled |

See [docs/scenarios/SCENARIOS.md](docs/scenarios/SCENARIOS.md) for all built-in scenarios
(`blocking_100`, `debate`, `offline`, `default`) and how to create your own.

## Documentation

- [Getting Started Tutorial](docs/tutorials/GETTING_STARTED.md) — Ollama + OpenRouter setup
- [Scenarios guide](docs/scenarios/SCENARIOS.md)
- [Architecture](docs/architecture/MODULARITY.md)
- [Stanford fork relationship](docs/architecture/UPSTREAM_RELATIONSHIP.md)
- [Docker guide](docs/guides/DOCKER.md)
- [Web UI dashboard](docs/guides/WEB_UI.md)
- [Database schema](docs/database/SCHEMA.md)
- [Developer onboarding](docs/guides/DEVELOPER_ONBOARDING.md)
- [Attribution / third-party notices](NOTICE)

## Research layers

Optional cognitive and social modules (disabled by default, activated via env flags):
`BiasLayer`, `HRM`, `RLIF`, `SEAL`, `SocialLearner`, `GameEngine`, `ConsensusEngine`, and more.

See [docs/research/LAYERS.md](docs/research/LAYERS.md) for the full list, enable flags, and status.

## Tests

```bash
pytest                          # unit tests (coverage gate ≥70%)
pytest tests/integration/       # integration (requires running server or Postgres)
```

Coverage excludes optional research layers (NEAT, social learning, HRM) — see
`[tool.coverage.run] omit` in `pyproject.toml`.

CI runs lint + unit + Postgres migration + smoke on every PR.
The 100-tick Ollama simulation is **manual/nightly** (too slow for PR CI).

## Performance

Historical benchmark data: [benchmarks/history.json](benchmarks/history.json)

Add your own run:
```bash
python scripts/run_sim_100_ticks_blocking.py --preset blocking_balanced --report output/bench.json
python benchmarks/add_entry.py output/bench.json
```
