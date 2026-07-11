from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from gen_agent.training.neat.config import NEATConfig
from gen_agent.training.neat.evaluation import NEATEvaluator
from gen_agent.training.neat.genome import NEATGenome, max_innovation


@dataclass
class Species:
    representative: NEATGenome
    members: list[NEATGenome] = field(default_factory=list)


class NEATPopulation:
    """Small NEAT population with distance-based species and elitism."""

    def __init__(self, cfg: NEATConfig, evaluator: NEATEvaluator) -> None:
        self.cfg = cfg
        self.evaluator = evaluator
        self.rng = np.random.default_rng(int(cfg.random_seed))
        self.genomes: list[NEATGenome] = [
            NEATGenome.minimal(cfg, self.rng) for _ in range(max(2, int(cfg.pop_size)))
        ]
        self.generation: int = 0
        self.best_genome: NEATGenome | None = None
        self.last_scores: list[float] = []
        self.last_agent_scores: dict[str, float] = {}
        self._next_innovation = max_innovation(self.genomes) + 1

    def run_generation(self, mode: str = "collective") -> NEATGenome:
        for genome in self.genomes:
            genome.fitness = self.evaluator.evaluate(genome, mode=mode)
        self.genomes.sort(key=lambda g: g.fitness, reverse=True)
        self.best_genome = self.genomes[0].clone()
        self.last_scores.append(float(self.best_genome.fitness))
        if len(self.last_scores) > 200:
            self.last_scores = self.last_scores[-200:]
        self.last_agent_scores = self.evaluator.evaluate_agents(self.best_genome, mode=mode)
        self._reproduce()
        self.generation += 1
        return self.best_genome.clone()

    def _species(self) -> list[Species]:
        species: list[Species] = []
        threshold = max(0.05, float(self.cfg.compatibility_threshold))
        for genome in self.genomes:
            placed = False
            for group in species:
                if genome.distance(group.representative) <= threshold:
                    group.members.append(genome)
                    placed = True
                    break
            if not placed:
                species.append(Species(representative=genome, members=[genome]))
        return species

    def _reproduce(self) -> None:
        target_size = max(2, int(self.cfg.pop_size))
        species = self._species()
        next_genomes: list[NEATGenome] = []

        elite_count = max(1, int(target_size * max(0.01, float(self.cfg.elite_fraction))))
        next_genomes.extend(g.clone() for g in self.genomes[:elite_count])

        while len(next_genomes) < target_size:
            group = species[int(self.rng.integers(0, len(species)))] if species else None
            pool = (group.members if group else self.genomes) or self.genomes
            survivors = self._survivors(pool)
            parent_a = survivors[int(self.rng.integers(0, len(survivors)))]
            if len(survivors) > 1 and self.rng.random() < self.cfg.crossover_rate:
                parent_b = survivors[int(self.rng.integers(0, len(survivors)))]
                child = NEATGenome.crossover(parent_a, parent_b, self.rng)
            else:
                child = parent_a.clone()
            self._next_innovation = child.mutate(self.cfg, self.rng, self._next_innovation)
            next_genomes.append(child)

        self.genomes = next_genomes[:target_size]

    def _survivors(self, genomes: list[NEATGenome]) -> list[NEATGenome]:
        ordered = sorted(genomes, key=lambda g: g.fitness, reverse=True)
        count = max(1, int(len(ordered) * max(0.05, min(1.0, self.cfg.survival_threshold))))
        return ordered[:count]
