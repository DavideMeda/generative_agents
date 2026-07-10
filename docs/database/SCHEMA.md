# Database Schema & Dual-Mode Strategy

## Dual-Mode Strategy

Gen_Agent uses a dual-mode database approach:

| Environment | Backend | Config |
|-------------|---------|--------|
| Local development / sim scripts | SQLite per-agent | `data/agents/{id}/memory.db` |
| Server / Docker / production | PostgreSQL | `DATABASE_URL=postgresql://...` |

### How It Works

The `engine_factory.build_memory()` function inspects `DATABASE_URL`:
- If it starts with `postgresql://` or `postgres://` → uses `PostgresMemoryBackend`
- Otherwise → uses `SQLiteMemoryBackend` per-agent in `data/agents/{id}/memory.db`

### Running Migrations

```bash
# local dev (SQLite): no migration needed, schema auto-created on first run

# production (PostgreSQL):
scripts/migrate.sh
# or inside Docker entrypoint:
alembic upgrade head
```

## Schema

```sql
CREATE TABLE memories (
    memory_id     TEXT PRIMARY KEY,
    agent_id      TEXT NOT NULL,
    content       TEXT NOT NULL,
    memory_type   TEXT NOT NULL,  -- observation | social | reflection | plan
    importance    FLOAT NOT NULL,
    created_at    FLOAT NOT NULL,
    last_accessed FLOAT NOT NULL,
    extra         JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_memories_agent ON memories(agent_id);
CREATE INDEX idx_memories_type  ON memories(agent_id, memory_type);
```

## Memory Types

| Type | Description | Scope |
|------|-------------|-------|
| `observation` | Perceived events in the world | sim |
| `social` | Dialogue/chat interactions | social |
| `reflection` | Agent introspection (LLM-generated) | any |
| `plan` | Stanford daily plan steps | sim |

## Reflection Triggers

Reflections are triggered automatically in `MemoryManager`:
1. **Modulo trigger**: every `REFLECTION_TRIGGER` (default: 5) new memories
2. **Salience trigger**: when a high-importance memory (≥ 7.0) is stored and ≥ 3 memories since last reflection

## Alembic Integration

Migrations live in `migrations/`. The `alembic.ini` points to the `DATABASE_URL` env var.

To add a new migration:
```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```
