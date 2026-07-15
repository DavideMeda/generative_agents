# Developer Onboarding

Get productive in under 60 minutes.

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10+ | [python.org](https://python.org) |
| Git | 2.40+ | [git-scm.com](https://git-scm.com) |
| Docker | 24+ | [docker.com](https://docker.com) |

## 1. Clone and set up

```bash
git clone https://github.com/DavideMeda/new-gen-agent.git
cd new-gen-agent

# Install dependencies (pyproject.toml is the single source of truth)
pip install -e ".[dev]"

# Environment
cp .env.example .env
# Edit .env — set LLM_PROVIDER (default: mock, no key needed to start)
```

> The old Stanford `requirements.txt` (Django, selenium, …) is **not used** here.
> This project uses `pyproject.toml` exclusively.

## 2. Run tests

```bash
pytest                         # all unit tests
pytest tests/unit/sim/         # only sim tests
pytest -v --tb=long            # verbose output
```

All tests must be green before opening a PR. Coverage gate: ≥70%.

## 3. Run the simulation locally

```bash
# Quick smoke test (no LLM needed)
python -c "
from gen_agent.sim.engine import SimEngine, SimConfig
from gen_agent.interfaces.sim_protocol import AgentConfig

engine = SimEngine(SimConfig(interaction_radius=5.0))
engine.register_agent(AgentConfig('a1', 'Alice', (0.0, 0.0)))
engine.register_agent(AgentConfig('a2', 'Bob',   (1.0, 0.0)))
for _ in range(3):
    result = engine.advance()
    print(f'Tick {result.tick}: {len(result.events)} events')
"

# 20-tick mock simulation (preset: fast)
python scripts/run_sim_100_ticks_blocking.py --llm mock --ticks 20 --preset fast

# 100-tick Ollama simulation (requires: ollama pull llama3.2:3b)
python scripts/run_sim_100_ticks_blocking.py --llm ollama --ticks 100
```

## 4. Codebase map

```
gen_agent/interfaces/    ← Start here when extending the system
gen_agent/sim/engine.py  ← Main simulation loop
gen_agent/memory/        ← Memory models, decay, SQLite backend
gen_agent/dialogue/      ← LLM conversation generation
gen_agent/telemetry/     ← Metrics and JSON reports
gen_agent/integrations/stanford/adapter.py  ← Stanford bridge
tests/                   ← Mirror of gen_agent/ structure
migrations/              ← Alembic DB migrations
scenarios/               ← Named simulation presets (fast, blocking_100, debate, offline)
```

## 5. Development workflow

```bash
# 1. Branch from main
git checkout main && git pull
git checkout -b feature/your-feature

# 2. Develop + test iteratively
pytest tests/unit/   # fast feedback loop

# 3. Lint before commit
ruff check gen_agent/ tests/
mypy gen_agent/ --ignore-missing-imports

# 4. Commit (conventional commits)
git commit -m "feat: your change description"

# 5. Open PR against main
git push origin feature/your-feature
```

Branch conventions:

| Branch | Purpose |
|--------|---------|
| `main` | Stable, CI-green, always deployable |
| `feature/*` | New features |
| `fix/*` | Bug fixes |
| `research/*` | Experimental — may not be stable |

## 6. Database migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe the change"
```

## 7. Run with Docker (dev)

```bash
# SQLite — simplest, no Postgres needed
docker compose up
# App: http://localhost:8000

# With PostgreSQL + pgAdmin
docker compose --profile postgres up
# App:     http://localhost:8000
# pgAdmin: http://localhost:5050
```

See [docs/guides/DOCKER.md](DOCKER.md) for full Docker reference.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: gen_agent` | Run `pip install -e ".[dev]"` from repo root |
| Stanford module not found | Normal in stub mode — adapter falls back gracefully |
| `DATABASE_URL` not set | Defaults to SQLite (`gen_agent.db` in current dir) |
| Tests import errors | Make sure `__init__.py` exists in all `tests/` subdirs |
