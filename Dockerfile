# syntax=docker/dockerfile:1.6
# ─── Stage 1: dependency resolver ────────────────────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
# Install production deps + postgres extra into isolated prefix
RUN pip install --no-cache-dir --prefix=/install ".[postgres]" --quiet

# ─── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

RUN groupadd --gid 1001 appgroup \
    && useradd  --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=deps /install /usr/local

# Application source
COPY --chown=appuser:appgroup gen_agent/        ./gen_agent/
COPY --chown=appuser:appgroup server/           ./server/
COPY --chown=appuser:appgroup config/           ./config/
COPY --chown=appuser:appgroup migrations/       ./migrations/
COPY --chown=appuser:appgroup scenarios/        ./scenarios/
COPY --chown=appuser:appgroup scripts/          ./scripts/
COPY --chown=appuser:appgroup reverie/          ./reverie/
COPY --chown=appuser:appgroup alembic.ini       .
COPY --chown=appuser:appgroup pyproject.toml    .
COPY --chown=appuser:appgroup LICENSE           .
COPY --chown=appuser:appgroup NOTICE            .

# Entrypoint script (migrate → server)
COPY --chown=appuser:appgroup docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:$PATH" \
    GEN_AGENT_DATA_DIR="/app/data"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
