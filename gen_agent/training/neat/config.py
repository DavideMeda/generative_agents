from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NEATConfig:
    """Runtime and evolution parameters for the built-in numpy NEAT backend."""

    input_size: int = 18
    output_size: int = 10
    hidden_nodes_initial: int = 2
    pop_size: int = 80
    species_size: int = 10
    survival_threshold: float = 0.2
    compatibility_threshold: float = 1.0
    weight_mutation_rate: float = 0.75
    weight_perturb_scale: float = 0.35
    add_connection_rate: float = 0.10
    add_node_rate: float = 0.04
    disable_connection_rate: float = 0.03
    crossover_rate: float = 0.75
    elite_fraction: float = 0.10
    random_seed: int = 1337
    mode: str = "movement"


@dataclass
class ContinuousNEATConfig:
    """Configuration accepted by StateStore.neat_continuous_start."""

    generations_per_cycle: int = 2
    sleep_seconds: float = 2.0
    pop_size: int = 80
    species_size: int = 10
    survival_threshold: float = 0.2
    compatibility_threshold: float = 1.0
    eval_ticks: int = 200
    eval_agents: int = 10
    mode: str = "collective"


def config_from_continuous(cfg: ContinuousNEATConfig, seed: int = 1337) -> NEATConfig:
    return NEATConfig(
        pop_size=max(2, int(cfg.pop_size)),
        species_size=max(1, int(cfg.species_size)),
        survival_threshold=max(0.05, min(1.0, float(cfg.survival_threshold))),
        compatibility_threshold=max(0.05, float(cfg.compatibility_threshold)),
        random_seed=int(seed),
        mode=str(cfg.mode or "collective"),
    )
