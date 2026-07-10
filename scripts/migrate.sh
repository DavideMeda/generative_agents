#!/usr/bin/env bash
# Run Alembic migrations against DATABASE_URL.
# Called by docker/entrypoint.sh before starting the server.
set -euo pipefail

echo "[migrate] Running alembic upgrade head..."
alembic upgrade head
echo "[migrate] Done."
