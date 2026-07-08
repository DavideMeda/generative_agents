# Gen_Agent

> Modular generative agent simulation — built on the [Stanford Generative Agents](https://github.com/joonspk-research/generative_agents) fork.

[![CI](https://github.com/DavideMeda/generative_agents/actions/workflows/ci.yml/badge.svg)](https://github.com/DavideMeda/generative_agents/actions/workflows/ci.yml)
[![Security](https://github.com/DavideMeda/generative_agents/actions/workflows/security.yml/badge.svg)](https://github.com/DavideMeda/generative_agents/actions/workflows/security.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)

## Quick start (5 minutes)

```bash
git clone https://github.com/DavideMeda/generative_agents.git
cd generative_agents

cp .env.example .env          # fill in OPENAI_API_KEY
pip install -e ".[dev]"
pytest                        # all tests green → you are ready
```

## Run with Docker

```bash
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up
```

App at `http://localhost:8000` — pgAdmin at `http://localhost:5050`.

## Project layout

```
gen_agent/           ← Gen_Agent application code (our namespace)
  interfaces/        ← Stable Protocols (MemoryProtocol, SimProtocol, …)
  memory/            ← Memory models, decay engine, SQLite backend
  sim/               ← SimEngine (tick loop + proximity detection)
  dialogue/          ← DialogueEngine (LLM-driven conversations)
  telemetry/         ← Metrics collection and JSON reports
  integrations/
    stanford/        ← ONLY place that imports from reverie/

reverie/             ← Stanford upstream code (read-only reference)
environment/         ← Stanford simulation environment
tests/               ← Unit + integration tests (pytest)
migrations/          ← Alembic database migrations
docs/                ← Architecture, guides, DB schema
```

## Documentation

| Doc | Link |
|-----|------|
| Architecture overview | [docs/architecture/OVERVIEW.md](docs/architecture/OVERVIEW.md) |
| Developer onboarding | [docs/guides/DEVELOPER_ONBOARDING.md](docs/guides/DEVELOPER_ONBOARDING.md) |
| Database schema | [docs/database/SCHEMA.md](docs/database/SCHEMA.md) |
| Branch strategy | [.github/BRANCH_STRATEGY.md](.github/BRANCH_STRATEGY.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |

## Key design decisions

- **Fork-first**: this repo *is* the Stanford fork — extensions live in `gen_agent/` namespace.
- **Single boundary**: only `gen_agent/integrations/stanford/adapter.py` imports from `reverie/`.
- **SQLite → Postgres**: set `DATABASE_URL` to swap; same Alembic migrations work for both.
- **Stub mode**: all components run without an LLM key (useful for CI and offline development).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Open PRs against `develop`, not `main`.
