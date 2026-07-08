# syntax=docker/dockerfile:1.6
# ─── Stage 1: dependency resolver ────────────────────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /build

# Install build tooling only in this stage — not shipped to final image
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
# Install production deps into an isolated prefix
RUN pip install --no-cache-dir --prefix=/install ".[dev]" --quiet

# ─── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user for security
RUN groupadd --gid 1001 appgroup \
    && useradd  --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Runtime-only system libraries (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built packages from deps stage
COPY --from=deps /install /usr/local

# Copy application source
COPY --chown=appuser:appgroup gen_agent/     ./gen_agent/
COPY --chown=appuser:appgroup server/        ./server/
COPY --chown=appuser:appgroup config/        ./config/
COPY --chown=appuser:appgroup reverie/       ./reverie/
COPY --chown=appuser:appgroup environment/   ./environment/
COPY --chown=appuser:appgroup pyproject.toml .

# Switch to non-root
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "server.main"]
