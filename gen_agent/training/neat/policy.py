from __future__ import annotations

from typing import Any

from gen_agent.training.neat.genome import NEATGenome
from gen_agent.training.neat.io_spec import NEATInputSpec, NEATOutputSpec
from gen_agent.training.neat.network import FeedForwardNetwork


class NEATPolicy:
    """Policy object attached to AgentSimState.neat_policy."""

    def __init__(
        self,
        genome: NEATGenome,
        input_spec: NEATInputSpec | None = None,
        output_spec: NEATOutputSpec | None = None,
    ) -> None:
        self.genome = genome.clone()
        self.input_spec = input_spec or NEATInputSpec(size=self.genome.input_size)
        self.output_spec = output_spec or NEATOutputSpec()
        self.network = FeedForwardNetwork(self.genome)

    def decide(self, agent: Any, world: Any, others: Any) -> dict[str, float]:
        inputs = self.input_spec.encode(agent, world, others or [])
        outputs = self.network.activate(inputs)
        return self.output_spec.decode(outputs)
