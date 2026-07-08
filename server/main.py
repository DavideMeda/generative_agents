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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.router import router
from server.state_store import StateStore
from server.tick_runner import TickRunner

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

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
