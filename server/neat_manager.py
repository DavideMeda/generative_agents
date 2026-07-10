"""NEAT manager for FastAPI server (wraps gen_agent.training.neat)."""
from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

NEAT_AVAILABLE = False
LiveNEATTrainingManager = None  # type: ignore

try:
    from gen_agent.training.neat.live_training import LiveNEATTrainingManager as _LiveNEATTrainingManager
    LiveNEATTrainingManager = _LiveNEATTrainingManager
    NEAT_AVAILABLE = True
except Exception as exc:
    logger.info("NEAT unavailable: %s", exc)


@dataclass
class NeatStatus:
    enabled: bool = False
    available: bool = False
    message: str = "NEAT module not installed"
    last_scores: list = field(default_factory=list)
    last_agent_scores: Dict[str, float] = field(default_factory=dict)


class NoopNeatManager:
    def __init__(self, _engine: Any) -> None:
        self._status = NeatStatus(available=NEAT_AVAILABLE)

    def start(self) -> NeatStatus:
        return self._status

    def stop(self) -> NeatStatus:
        return self._status

    def status(self) -> Dict[str, Any]:
        return asdict(self._status)

    def load_best(self, path: str) -> Dict[str, Any]:
        return {"ok": False, "error": "neat_not_available", "path": path}

    def start_continuous(self, cfg: Optional[Any] = None) -> Dict[str, Any]:
        return {"ok": False, "error": "neat_not_available"}

    def stop_continuous(self) -> Dict[str, Any]:
        return {"ok": False, "error": "neat_not_available"}


def create_neat_manager(engine: Any) -> Any:
    if NEAT_AVAILABLE and LiveNEATTrainingManager is not None:
        from gen_agent.training.neat.config import NEATConfig
        seed = int(getattr(getattr(engine, "config", None), "seed", 1337))
        mode = str(os.environ.get("GEN_AGENT_NEAT_MODE", "movement")).strip().lower()
        if mode not in ("emotions", "movement", "collective"):
            mode = "movement"
        return LiveNEATTrainingManager(engine, config=NEATConfig(random_seed=seed, mode=mode))
    return NoopNeatManager(engine)
