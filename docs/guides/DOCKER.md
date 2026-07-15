# Docker Guide

## Local Development (SQLite — simplest)

```bash
docker compose up
# App: http://localhost:8000
```

SQLite is the default storage — no Postgres needed.
Hot-reload is enabled: local source changes are reflected immediately.

## Local Development with PostgreSQL

```bash
# Optionally set a custom password in .env first
docker compose --profile postgres up
# App:     http://localhost:8000
# pgAdmin: http://localhost:5050 (admin@gen-agent.dev / admin)
```

## Stanford UI (Django frontend)

```bash
docker compose -f docker-compose.yml -f docker-compose.stanford.yml up
# Backend: http://localhost:8000
# Stanford UI: http://localhost:8080
```

Requires `environment/frontend_server/` on disk. See [STANFORD_UI.md](STANFORD_UI.md).

## Production (PostgreSQL + nginx TLS)

```bash
# 1. Copy and fill in production env vars
cp .env.example .env
# Edit .env: set POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

# 2. Place TLS certificates
mkdir -p config/certs
# copy fullchain.pem + privkey.pem into config/certs/

# 3. Start
docker compose -f docker-compose.prod.yml up -d
```

The production compose file uses the pre-built image from GHCR
(`ghcr.io/davidemeda/new-gen-agent:latest`) and adds nginx for TLS termination.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | (empty = SQLite) | PostgreSQL DSN for production |
| `LLM_PROVIDER` | `mock` | `ollama`, `openrouter`, or `mock` |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model name |
| `OLLAMA_TIMEOUT` | `300` | LLM call timeout in seconds |
| `GEN_AGENT_DATA_DIR` | `data` | Directory for SQLite DBs and output |
| `ENABLE_STANFORD_WORKER` | `false` | Enable background cognition worker |
| `ENABLE_NEAT` | `false` | Enable NEAT evolution |
| `ENABLE_GAME_THEORY` | `false` | Enable game-theoretic interaction outcomes |

See `.env.example` for the full list of flags.

## Health Check

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## Building the image manually

```bash
docker build -t gen-agent:latest .
docker run -p 8000:8000 -e LLM_PROVIDER=mock gen-agent:latest
```
