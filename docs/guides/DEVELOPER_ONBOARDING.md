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
git clone https://github.com/DavideMeda/generative_agents.git
cd generative_agents

# Configure remotes (our fork + Stanford upstream for syncs)
git remote add upstream https://github.com/joonspk-research/generative_agents.git
git remote -v   # verify: origin + upstream

# Install dependencies
pip install -e ".[dev]"

# Environment
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY
```

## 2. Run tests

```bash
pytest                         # all unit tests
pytest tests/unit/sim/         # only sim tests
pytest -v --tb=long            # verbose output
```

All tests must be green before opening a PR.

## 3. Run the simulation locally

```bash
# Minimal example (stub mode — no LLM key needed)
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
```

## 5. Development workflow

```bash
# 1. Branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/your-feature

# 2. Develop + test iteratively
pytest tests/unit/   # fast feedback loop

# 3. Lint before commit
ruff check gen_agent/ tests/
mypy gen_agent/

# 4. Commit (conventional commits)
git commit -m "feat: your change description"

# 5. Open PR against develop
git push origin feature/your-feature
# → open PR on GitHub
```

## 6. Database migrations

```bash
# Apply migrations
./scripts/migrate.sh upgrade

# Create a new migration after model changes
./scripts/migrate.sh revision "describe the change"
```

## 7. Run with Docker (dev)

```bash
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up
# App:     http://localhost:8000
# pgAdmin: http://localhost:5050
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: gen_agent` | Run `pip install -e ".[dev]"` from repo root |
| Stanford module not found | Normal in stub mode — adapter falls back gracefully |
| `DATABASE_URL` not set | Defaults to `sqlite:///./gen_agent.db` |
| Tests import errors | Make sure `__init__.py` exists in all `tests/` subdirs |
