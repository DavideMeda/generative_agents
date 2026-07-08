"""
TickRunner — background thread that advances the simulation tick-by-tick
and broadcasts state to all connected WebSocket clients.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any, Dict, Set

logger = logging.getLogger(__name__)

# Global set of active WebSocket queues (one per connected client)
_ws_queues: Set[asyncio.Queue] = set()  # type: ignore[type-arg]
_ws_lock = threading.Lock()


def register_ws(queue: asyncio.Queue) -> None:  # type: ignore[type-arg]
    with _ws_lock:
        _ws_queues.add(queue)


def unregister_ws(queue: asyncio.Queue) -> None:  # type: ignore[type-arg]
    with _ws_lock:
        _ws_queues.discard(queue)


def _broadcast(payload: Dict[str, Any]) -> None:
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
        logger.info("TickRunner started (interval=%.2fs)", self._interval)
        while True:
            if not self._store.running or self._store.engine is None:
                time.sleep(0.1)
                continue
            try:
                result = self._store.engine.advance()
                snap = self._store.engine.snapshot()
                payload = {
                    "tick": result.tick,
                    "events": result.events,
                    "agents": snap.get("agents", {}),
                    "stats": self._store.engine.stats(),
                }
                _broadcast(payload)
            except Exception as exc:
                logger.error("TickRunner error at tick: %s", exc)
            time.sleep(self._interval)
