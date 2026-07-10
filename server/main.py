"""
Gen_Agent Server — FastAPI application entry point.

Starts a background TickRunner thread and exposes REST + WebSocket endpoints.

Run:
    python scripts/run_server.py
    # or directly:
    uvicorn server.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import os

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.router import router
from server.state_store import StateStore
from server.tick_runner import TickRunner


def _configure_logging() -> None:
    """
    Configura structlog in modalità dev (console leggibile) o prod (JSON).
    LOG_FORMAT=json → ndjson per aggregatori (Loki, CloudWatch, etc.)
    LOG_FORMAT=dev  → console colorata (default)
    Documentazione: docs/guides/OBSERVABILITY.md
    """
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_format = os.getenv("LOG_FORMAT", "dev").lower()

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processor=renderer,
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)


_configure_logging()
logger = structlog.get_logger(__name__)

app = FastAPI(
    title="Gen_Agent Simulation Server",
    description="Modular generative agent simulation — built on Stanford GA fork",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

_tick_runner: TickRunner | None = None


@app.on_event("startup")
def _startup() -> None:
    global _tick_runner
    store = StateStore.get()
    interval = float(os.getenv("TICK_INTERVAL_SEC", "1.0"))
    _tick_runner = TickRunner(store, tick_interval_sec=interval)
    _tick_runner.start()
    logger.info("Gen_Agent server started. TickRunner running (interval=%.1fs).", interval)


@app.on_event("shutdown")
def _shutdown() -> None:
    store = StateStore.get()
    store.running = False
    logger.info("Gen_Agent server shutting down.")
