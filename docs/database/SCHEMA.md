# Database Schema

## Strategy

Gen_Agent starts with **SQLite** for zero-config local development and switches to **PostgreSQL** for production via the `DATABASE_URL` environment variable.

The storage interface (`SQLiteMemoryBackend`) is decoupled from the manager — swapping backends requires only a constructor change, no business logic rewrite.

## Migration tool: Alembic

```bash
# Apply all pending migrations
./scripts/migrate.sh upgrade

# Roll back one step
./scripts/migrate.sh downgrade -1

# Create a new migration after model changes
./scripts/migrate.sh revision "describe your change"
```

Set `DATABASE_URL` before running:

```bash
# SQLite (default)
export DATABASE_URL=sqlite:///./gen_agent.db

# PostgreSQL
export DATABASE_URL=postgresql://user:password@localhost:5432/gen_agent
```

## Tables

### `memories`

| Column         | Type    | Notes                              |
|----------------|---------|------------------------------------|
| `memory_id`    | TEXT PK | UUID v4                            |
| `agent_id`     | TEXT    | Owner agent — indexed              |
| `content`      | TEXT    | Raw memory text                    |
| `memory_type`  | TEXT    | `observation` / `reflection` / `plan` |
| `importance`   | REAL    | 0.0 – 10.0                        |
| `created_at`   | REAL    | Unix timestamp                     |
| `last_accessed`| REAL    | Unix timestamp — updated on touch  |
| `extra`        | TEXT    | JSON blob for extension fields     |

**Indexes:**
- `idx_memories_agent` on `(agent_id)` — all queries filter by agent.
- `idx_memories_type` on `(agent_id, memory_type)` — type-filtered retrieval.

## Adding PostgreSQL in production

1. Provision a Postgres 16 instance.
2. Set `DATABASE_URL=postgresql://user:pass@host:5432/gen_agent`.
3. Run `./scripts/migrate.sh upgrade`.
4. The `SQLiteMemoryBackend` will still work for local dev — no code changes needed.

> For a full PostgreSQL backend, extend `SQLiteMemoryBackend` into a `PostgresMemoryBackend`
> that shares the same `MemoryProtocol` interface.
