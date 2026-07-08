"""
StateStore — thread-safe singleton holding the active SimEngine instance.

The server creates one engine at startup and all routes access it here.
"""
from __future__ import annotations

import threading
from typing import Optional

from gen_agent.sim.engine import SimEngine


class StateStore:
    _instance: Optional["StateStore"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.engine: Optional[SimEngine] = None
        self.running: bool = False

    @classmethod
    def get(cls) -> "StateStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = StateStore()
        return cls._instance
