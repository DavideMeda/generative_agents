# Docker Guide

## Local Development (SQLite, no Postgres)

```bash
docker compose -f docker-compose.dev.yml up
```

This starts only the server, using SQLite for memory storage. No migration needed.

## Production (PostgreSQL)

```bash
# Copy and fill in environment variables
cp .env.example .env
# Edit .env: set DATABASE_URL, OLLAMA_MODEL, etc.

docker compose up
```

On first start, the entrypoint automatically runs `alembic upgrade head` before
starting the server.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | (empty = SQLite) | PostgreSQL DSN for production |
| `LLM_PROVIDER` | `ollama` | `ollama` or `mock` |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model name |
| `OLLAMA_TIMEOUT` | `300` | LLM call timeout in seconds |
| `GEN_AGENT_DATA_DIR` | `data` | Directory for SQLite DBs and output |
| `ENABLE_STANFORD_WORKER` | `1` | Enable background cognition worker |
| `ENABLE_NEAT` | `0` | Enable NEAT evolution |
| `ENABLE_GAME_THEORY` | `0` | Enable game-theoretic interaction outcomes |

## Health Check

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## Building Manually

```bash
docker build -t gen-agent:latest .
docker run -p 8000:8000 -e LLM_PROVIDER=mock gen-agent:latest
```

## TLS / Certificates

For development, TLS is disabled. For production, place TLS termination at
your reverse proxy (nginx/Caddy) or set `SSL_KEYFILE` and `SSL_CERTFILE` env
vars (passed to uvicorn).
