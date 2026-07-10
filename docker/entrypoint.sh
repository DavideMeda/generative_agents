#!/usr/bin/env bash
# Entrypoint for production Docker container.
# 1. Run Alembic migrations if DATABASE_URL is set (PostgreSQL prod mode).
# 2. Start the FastAPI server.
set -euo pipefail

echo "[entrypoint] Starting Gen_Agent..."

if [[ -n "${DATABASE_URL:-}" ]]; then
    echo "[entrypoint] Running alembic upgrade head..."
    alembic upgrade head
    echo "[entrypoint] Migrations complete."
else
    echo "[entrypoint] No DATABASE_URL — using SQLite (local dev mode)."
fi

echo "[entrypoint] Starting server..."
exec "$@"
