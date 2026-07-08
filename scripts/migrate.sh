#!/usr/bin/env bash
# Database migration helper — wraps alembic commands.
# Usage:
#   ./scripts/migrate.sh upgrade       # apply all pending migrations
#   ./scripts/migrate.sh downgrade -1  # roll back one step
#   ./scripts/migrate.sh revision "add agent table"  # create a new revision
set -euo pipefail

CMD="${1:-upgrade}"
shift || true

case "$CMD" in
  upgrade)   alembic upgrade head "$@" ;;
  downgrade) alembic downgrade "$@" ;;
  revision)  alembic revision --autogenerate -m "$*" ;;
  history)   alembic history --verbose ;;
  current)   alembic current ;;
  *)
    echo "Unknown command: $CMD"
    echo "Available: upgrade | downgrade | revision | history | current"
    exit 1
    ;;
esac
