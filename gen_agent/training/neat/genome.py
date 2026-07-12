from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np

from gen_agent.training.neat.config import NEATConfig


@dataclass
class ConnectionGene:
    in_node: int
    out_node: int
    weight: float
    enabled: bool = True
    innovation: int = 0


@dataclass
class NEATGenome:
    input_size: int
    output_size: int
    hidden_nodes: list[int] = field(default_factory=list)
    connections: list[ConnectionGene] = field(default_factory=list)
    fitness: float = 0.0

    @property
    def output_nodes(self) -> list[int]:
        return list(range(self.input_size, self.input_size + self.output_size))

    @property
    def node_count(self) -> int:
        return self.input_size + self.output_size + len(self.hidden_nodes)

    def clone(self) -> NEATGenome:
        return NEATGenome(
            input_size=self.input_size,
            output_size=self.output_size,
            hidden_nodes=list(self.hidden_nodes),
            connections=[
                ConnectionGene(c.in_node, c.out_node, c.weight, c.enabled, c.innovation)
                for c in self.connections
            ],
            fitness=float(self.fitness),
        )

    @classmethod
    def minimal(cls, cfg: NEATConfig, rng: np.random.Generator) -> NEATGenome:
        hidden = [
            cfg.input_size + cfg.output_size + idx
            for idx in range(max(0, cfg.hidden_nodes_initial))
        ]
        genome = cls(input_size=cfg.input_size, output_size=cfg.output_size, hidden_nodes=hidden)
        innovation = 1
        for out_node in genome.output_nodes:
            for in_node in range(cfg.input_size):
                if rng.random() < 0.65:
                    genome.connections.append(
                        ConnectionGene(
                            in_node=in_node,
                            out_node=out_node,
                            weight=float(rng.normal(0.0, 0.7)),
                            enabled=True,
                            innovation=innovation,
                        )
                    )
                    innovation += 1
        for hidden_node in hidden:
            source = int(rng.integers(0, cfg.input_size))
            target = int(rng.choice(genome.output_nodes))
            genome.connections.append(
                ConnectionGene(source, hidden_node, float(rng.normal(0.0, 0.7)), True, innovation)
            )
            innovation += 1
            genome.connections.append(
                ConnectionGene(hidden_node, target, float(rng.normal(0.0, 0.7)), True, innovation)
            )
            innovation += 1
        return genome

    def mutate(self, cfg: NEATConfig, rng: np.random.Generator, innovation_start: int = 1) -> int:
        next_innovation = int(innovation_start)
        for conn in self.connections:
            if rng.random() < cfg.weight_mutation_rate:
                conn.weight += float(rng.normal(0.0, cfg.weight_perturb_scale))
            if rng.random() < cfg.disable_connection_rate:
                conn.enabled = False
        if rng.random() < cfg.add_connection_rate:
            next_innovation = self._mutate_add_connection(rng, next_innovation)
        if rng.random() < cfg.add_node_rate:
            next_innovation = self._mutate_add_node(rng, next_innovation)
        return next_innovation

    def _mutate_add_connection(self, rng: np.random.Generator, innovation: int) -> int:
        possible_sources = list(range(self.input_size)) + list(self.hidden_nodes)
        possible_targets = list(self.hidden_nodes) + self.output_nodes
        existing = {(c.in_node, c.out_node) for c in self.connections}
        for _ in range(32):
            src = int(rng.choice(possible_sources))
            dst = int(rng.choice(possible_targets))
            if src == dst or (src, dst) in existing:
                continue
            if dst < self.input_size:
                continue
            self.connections.append(
                ConnectionGene(src, dst, float(rng.normal(0.0, 0.8)), True, int(innovation))
            )
            return innovation + 1
        return innovation

    def _mutate_add_node(self, rng: np.random.Generator, innovation: int) -> int:
        enabled = [c for c in self.connections if c.enabled]
        if not enabled:
            return innovation
        conn = enabled[int(rng.integers(0, len(enabled)))]
        conn.enabled = False
        new_node = max([self.input_size + self.output_size - 1] + self.hidden_nodes) + 1
        self.hidden_nodes.append(new_node)
        self.connections.append(ConnectionGene(conn.in_node, new_node, 1.0, True, int(innovation)))
        self.connections.append(
            ConnectionGene(new_node, conn.out_node, conn.weight, True, int(innovation) + 1)
        )
        return innovation + 2

    def distance(self, other: NEATGenome) -> float:
        by_innovation: dict[int, ConnectionGene] = {c.innovation: c for c in self.connections}
        other_by_innovation: dict[int, ConnectionGene] = {
            c.innovation: c for c in other.connections
        }
        all_keys = set(by_innovation) | set(other_by_innovation)
        if not all_keys:
            return 0.0
        disjoint = 0
        weight_delta = 0.0
        matching = 0
        for key in all_keys:
            a = by_innovation.get(key)
            b = other_by_innovation.get(key)
            if a is None or b is None:
                disjoint += 1
            else:
                matching += 1
                weight_delta += abs(a.weight - b.weight)
        return (disjoint / max(1, len(all_keys))) + (weight_delta / max(1, matching))

    @staticmethod
    def crossover(
        parent_a: NEATGenome, parent_b: NEATGenome, rng: np.random.Generator
    ) -> NEATGenome:
        if parent_b.fitness > parent_a.fitness:
            parent_a, parent_b = parent_b, parent_a
        child = NEATGenome(
            input_size=parent_a.input_size,
            output_size=parent_a.output_size,
            hidden_nodes=sorted(set(parent_a.hidden_nodes) | set(parent_b.hidden_nodes)),
        )
        b_by_innovation = {c.innovation: c for c in parent_b.connections}
        for conn_a in parent_a.connections:
            conn_b = b_by_innovation.get(conn_a.innovation)
            chosen = conn_b if conn_b is not None and rng.random() < 0.5 else conn_a
            child.connections.append(
                ConnectionGene(
                    chosen.in_node,
                    chosen.out_node,
                    chosen.weight,
                    chosen.enabled,
                    chosen.innovation,
                )
            )
        return child

    def to_arrays(self) -> dict[str, np.ndarray]:  # type: ignore[type-arg]
        data = np.asarray(
            [
                [c.in_node, c.out_node, c.weight, 1.0 if c.enabled else 0.0, c.innovation]
                for c in self.connections
            ],
            dtype=np.float64,
        )
        return {
            "input_size": np.asarray([self.input_size], dtype=np.int64),
            "output_size": np.asarray([self.output_size], dtype=np.int64),
            "hidden_nodes": np.asarray(self.hidden_nodes, dtype=np.int64),
            "connections": data,
            "fitness": np.asarray([self.fitness], dtype=np.float64),
        }

    @classmethod
    def from_arrays(cls, arrays: dict[str, np.ndarray]) -> NEATGenome:  # type: ignore[type-arg]
        genome = cls(
            input_size=int(arrays["input_size"][0]),
            output_size=int(arrays["output_size"][0]),
            hidden_nodes=[
                int(v) for v in arrays.get("hidden_nodes", np.asarray([], dtype=np.int64))
            ],
            fitness=float(arrays.get("fitness", np.asarray([0.0]))[0]),
        )
        for row in arrays.get("connections", np.empty((0, 5), dtype=np.float64)):
            genome.connections.append(
                ConnectionGene(
                    in_node=int(row[0]),
                    out_node=int(row[1]),
                    weight=float(row[2]),
                    enabled=bool(row[3] >= 0.5),
                    innovation=int(row[4]),
                )
            )
        return genome


def max_innovation(genomes: Iterable[NEATGenome]) -> int:
    value = 0
    for genome in genomes:
        for conn in genome.connections:
            value = max(value, int(conn.innovation))
    return value
