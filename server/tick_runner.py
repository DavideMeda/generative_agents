"""
TickRunner — background thread that advances the simulation tick-by-tick
and broadcasts state to all connected WebSocket clients.

WS envelope format (schema_version "1"):
  {
    "schema_version": "1",
    "type": "tick_result",
    "tick": <int>,
    "timestamp": <ISO-8601 UTC>,
    "data": { "events": [...], "agents": {...}, "stats": {...} }
  }
"""
from __future__ import annotations

import asyncio
import datetime
import json
import threading
import time
from typing import Any

import structlog

WS_SCHEMA_VERSION = "1"

logger = structlog.get_logger(__name__)

# Global set of active WebSocket queues (one per connected client)
_ws_queues: set[asyncio.Queue] = set()  # type: ignore[type-arg]
_ws_lock = threading.Lock()


def register_ws(queue: asyncio.Queue) -> None:  # type: ignore[type-arg]
    with _ws_lock:
        _ws_queues.add(queue)


def unregister_ws(queue: asyncio.Queue) -> None:  # type: ignore[type-arg]
    with _ws_lock:
        _ws_queues.discard(queue)


def _make_envelope(event_type: str, *, tick: int, data: dict[str, Any]) -> dict[str, Any]:
    """Build a versioned WS envelope. Schema defined in docs/guides/WEBSOCKET_PROTOCOL.md."""
    return {
        "schema_version": WS_SCHEMA_VERSION,
        "type": event_type,
        "tick": tick,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "data": data,
    }


def _broadcast(payload: dict[str, Any]) -> None:
    """Push payload to all registered WS queues (non-blocking, thread-safe)."""
    msg = json.dumps(payload)
    with _ws_lock:
        dead: list = []
        for q in _ws_queues:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass
            except Exception:
                dead.append(q)
        for q in dead:
            _ws_queues.discard(q)


class TickRunner(threading.Thread):
    """
    Runs engine.advance() in a daemon thread at the configured tick rate.
    Broadcasts each TickResult as JSON to all WebSocket clients.
    """

    def __init__(self, store: Any, tick_interval_sec: float = 1.0) -> None:
        super().__init__(daemon=True, name="TickRunner")
        self._store = store
        self._interval = tick_interval_sec

    def run(self) -> None:
        logger.info("tick_runner.started", interval=self._interval)
        while True:
            if not self._store.running or self._store.engine is None:
                time.sleep(0.1)
                continue
            try:
                result = self._store.engine.advance()
                snap = self._store.engine.snapshot()
                agents_snap = snap.get("agents", {})
                payload = _make_envelope(
                    "tick_result",
                    tick=result.tick,
                    data={
                        "events": result.events,
                        "agents": agents_snap,
                        "stats": self._store.engine.stats(),
                    },
                )
                _broadcast(payload)
                # optional Stanford UI file export
                try:
                    from server.stanford_exporter import get_exporter
                    exp = get_exporter()
                    if exp is not None:
                        exp.export_tick(result.tick, agents_snap)
                except Exception:
                    pass  # ponytail: export is best-effort, never blocks tick loop
                logger.debug(
                    "tick_runner.tick_advanced",
                    tick=result.tick,
                    events=len(result.events),
                    ws_clients=len(_ws_queues),
                )
            except Exception as exc:
                logger.error("tick_runner.error", exc_info=exc)
            time.sleep(self._interval)
