from __future__ import annotations

from pathlib import Path

import numpy as np

from gen_agent.training.neat.genome import NEATGenome

PathLike = str | Path


def save_individual(genome: NEATGenome, path: PathLike) -> str:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, **genome.to_arrays())
    return str(out)


def load_individual(path: PathLike) -> NEATGenome:
    src = Path(path)
    with np.load(src, allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    return NEATGenome.from_arrays(arrays)
