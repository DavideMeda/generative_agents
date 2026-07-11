from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from gen_agent.training.neat.config import ContinuousNEATConfig, NEATConfig, config_from_continuous
from gen_agent.training.neat.evaluation import NEATEvaluator
from gen_agent.training.neat.genome import NEATGenome
from gen_agent.training.neat.persistence import load_individual, save_individual
from gen_agent.training.neat.policy import NEATPolicy
from gen_agent.training.neat.population import NEATPopulation

logger = logging.getLogger(__name__)


@dataclass
class NEATStatus:
    enabled: bool = False
    available: bool = True
    message: str = "NEAT ready"
    mode: str = "movement"
    generation: int = 0
    continuous_running: bool = False
    best_fitness: float = 0.0
    best_path: str = "outputs/neat/best_individual.npz"
    last_scores: list = field(default_factory=list)
    last_agent_scores: dict[str, float] = field(default_factory=dict)


class LiveNEATTrainingManager:
    """Live NEAT manager used by batch scripts and the FastAPI server."""

    def __init__(
        self,
        engine: Any,
        config: NEATConfig | None = None,
        best_path: str = "outputs/neat/best_individual.npz",
    ) -> None:
        self.engine = engine
        seed = int(getattr(getattr(engine, "config", None), "seed", 1337))
        self.config = config or NEATConfig(random_seed=seed)
        self.best_path = str(best_path)
        self.evaluator = NEATEvaluator(engine)
        self.population = NEATPopulation(self.config, self.evaluator)
        self.best_genome: NEATGenome | None = None
        self._status = NEATStatus(best_path=self.best_path)
        self._lock = threading.RLock()
        self._continuous_stop = threading.Event()
        self._continuous_thread: threading.Thread | None = None

    def start(self) -> NEATStatus:
        with self._lock:
            if self.best_genome is None:
                self.best_genome = self._load_best_if_exists() or self.population.run_generation(
                    mode=self.config.mode
                )
            self._apply_policy(self.best_genome, mode=self._engine_mode(self.config.mode))
            self._update_status(enabled=True, message="NEAT policy applied")
            return self._status

    def stop(self) -> NEATStatus:
        with self._lock:
            self.stop_continuous()
            try:
                self.engine.disable_neat_for_all()
            except Exception:
                logger.warning("Unable to disable NEAT policies on engine", exc_info=True)
            self._status.enabled = False
            self._status.message = "NEAT disabled"
            return self._status

    def status(self) -> dict[str, Any]:
        with self._lock:
            return asdict(self._status)

    def load_best(self, path: str) -> dict[str, Any]:
        with self._lock:
            try:
                genome = load_individual(path)
                self.best_genome = genome
                self.best_path = str(path)
                self._apply_policy(genome, mode=self._engine_mode(self.config.mode))
                self._status.best_path = str(path)
                self._update_status(enabled=True, message=f"Loaded NEAT individual: {path}")
                return {"ok": True, "path": str(path), "status": self.status()}
            except Exception as exc:
                logger.warning("Unable to load NEAT individual from %s", path, exc_info=True)
                return {"ok": False, "error": str(exc), "path": str(path)}

    def load_best_for_agent(self, agent_id: str, path: str) -> dict[str, Any]:
        with self._lock:
            try:
                genome = load_individual(path)
                policy = NEATPolicy(genome)
                self.engine.set_neat_policy_for_agent(
                    agent_id, policy, mode=self._engine_mode(self.config.mode)
                )
                self.best_genome = genome
                self._update_status(enabled=True, message=f"Loaded NEAT for agent {agent_id}")
                return {
                    "ok": True,
                    "agent_id": str(agent_id),
                    "path": str(path),
                    "status": self.status(),
                }
            except Exception as exc:
                logger.warning(
                    "Unable to load NEAT individual for agent %s", agent_id, exc_info=True
                )
                return {
                    "ok": False,
                    "error": str(exc),
                    "agent_id": str(agent_id),
                    "path": str(path),
                }

    def start_continuous(self, cfg: ContinuousNEATConfig | None = None) -> dict[str, Any]:
        with self._lock:
            if cfg is not None:
                seed = int(getattr(getattr(self.engine, "config", None), "seed", 1337))
                self.config = config_from_continuous(cfg, seed=seed)
                self.evaluator = NEATEvaluator(
                    self.engine,
                    eval_ticks=int(cfg.eval_ticks),
                    eval_agents=int(cfg.eval_agents),
                )
                self.population = NEATPopulation(self.config, self.evaluator)
            if self._continuous_thread and self._continuous_thread.is_alive():
                return {"ok": True, "status": self.status()}
            self._continuous_stop.clear()
            self._continuous_thread = threading.Thread(
                target=self._continuous_loop,
                args=(cfg or ContinuousNEATConfig(),),
                name="gen-agent-neat-continuous",
                daemon=True,
            )
            self._continuous_thread.start()
            self._status.continuous_running = True
            self._status.message = "NEAT continuous training running"
            return {"ok": True, "status": self.status()}

    def stop_continuous(self) -> dict[str, Any]:
        self._continuous_stop.set()
        thread = self._continuous_thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._status.continuous_running = False
        return {"ok": True, "status": self.status()}

    def _continuous_loop(self, cfg: ContinuousNEATConfig) -> None:
        while not self._continuous_stop.is_set():
            try:
                generations = max(1, int(cfg.generations_per_cycle))
                for _ in range(generations):
                    with self._lock:
                        self.best_genome = self.population.run_generation(mode=cfg.mode)
                        self._apply_policy(self.best_genome, mode=self._engine_mode(cfg.mode))
                        save_individual(self.best_genome, self.best_path)
                        self._update_status(
                            enabled=True, message="NEAT continuous generation completed"
                        )
                self._continuous_stop.wait(max(0.1, float(cfg.sleep_seconds)))
            except Exception as exc:
                logger.warning("NEAT continuous training cycle failed: %s", exc, exc_info=True)
                self._status.message = f"NEAT continuous error: {exc}"
                self._continuous_stop.wait(max(1.0, float(cfg.sleep_seconds)))
        with self._lock:
            self._status.continuous_running = False

    def _apply_policy(self, genome: NEATGenome, mode: str) -> None:
        def factory(_agent: Any) -> NEATPolicy:
            return NEATPolicy(genome)

        self.engine.set_neat_policy_for_all(factory, mode=mode)

    def _load_best_if_exists(self) -> NEATGenome | None:
        path = Path(self.best_path)
        if not path.exists():
            return None
        try:
            return load_individual(path)
        except Exception:
            logger.warning(
                "Existing NEAT best individual could not be loaded: %s", path, exc_info=True
            )
            return None

    def _update_status(self, enabled: bool, message: str) -> None:
        if self.best_genome is not None:
            self._status.best_fitness = float(self.best_genome.fitness)
        self._status.enabled = bool(enabled)
        self._status.available = True
        self._status.message = str(message)
        self._status.mode = self._engine_mode(self.config.mode)
        self._status.generation = int(self.population.generation)
        self._status.best_path = self.best_path
        self._status.last_scores = list(self.population.last_scores)
        self._status.last_agent_scores = dict(self.population.last_agent_scores)

    def _engine_mode(self, mode: str) -> str:
        mode_s = str(mode or "movement").strip().lower()
        if mode_s == "emotions":
            return "emotions"
        return "movement"
