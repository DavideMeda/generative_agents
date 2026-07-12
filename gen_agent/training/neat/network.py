from __future__ import annotations

import numpy as np

from gen_agent.training.neat.genome import NEATGenome


class FeedForwardNetwork:
    """Small acyclic neural network built from a NEATGenome."""

    def __init__(self, genome: NEATGenome):
        self.genome = genome.clone()
        self.input_size = int(genome.input_size)
        self.output_size = int(genome.output_size)
        self.output_nodes = list(genome.output_nodes)
        self.hidden_nodes = sorted(set(genome.hidden_nodes))
        self.node_order = self.hidden_nodes + self.output_nodes
        self.incoming: dict[int, list[tuple[int, float]]] = {}
        for conn in genome.connections:
            if not conn.enabled:
                continue
            self.incoming.setdefault(int(conn.out_node), []).append(
                (int(conn.in_node), float(conn.weight))
            )

    def activate(self, inputs: np.ndarray) -> np.ndarray:  # type: ignore[type-arg]
        values: dict[int, float] = {}
        arr = np.asarray(inputs, dtype=np.float64)
        if arr.size < self.input_size:
            arr = np.pad(arr, (0, self.input_size - arr.size), constant_values=0.0)
        for idx in range(self.input_size):
            values[idx] = float(arr[idx])
        for node in self.node_order:
            total = 0.0
            for source, weight in self.incoming.get(node, []):
                total += values.get(source, 0.0) * weight
            values[node] = float(np.tanh(np.clip(total, -12.0, 12.0)))
        return np.asarray([values.get(node, 0.0) for node in self.output_nodes], dtype=np.float64)
