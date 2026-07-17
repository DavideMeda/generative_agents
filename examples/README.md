# Examples

Ready-to-run scripts covering the most common use cases.
All scripts can be executed from the repo root:

```bash
cd new-gen-agent
pip install -e ".[dev]"
python examples/<script>.py
```

## Overview

| Script | Tick | Agents | LLM | Feature | Expected time |
|--------|------|--------|-----|---------|---------------|
| `hello_world.py` | 10 | 3 | mock | Minimal simulation | ~5 s |
| `ollama_simple.py` | 20 | 3 | Ollama | Real LLM dialogues | ~2–5 min |
| `openrouter_api.py` | 20 | 3 | OpenRouter | Cloud API (free tier) | ~1–3 min |
| `cognitive_biases.py` | 30 | 5 | mock | Cognitive bias layer demo | ~30 s |
| `custom_scenario.py` | 15 | 4 | mock | Custom world + scenario | ~10 s |

## Quick start

```bash
# No dependencies beyond the pip install — runs immediately
python examples/hello_world.py
```

## Ollama (local LLM)

```bash
ollama pull llama3.2:3b
python examples/ollama_simple.py

# Use a different model
OLLAMA_MODEL=llama3.1:8b python examples/ollama_simple.py
```

If Ollama is not running, the script falls back to mock automatically.

## OpenRouter (cloud API, free tier)

```bash
# Get a free key at https://openrouter.ai
export OPENROUTER_API_KEY=sk-or-...
python examples/openrouter_api.py

# Use a specific model
OPENROUTER_MODEL=openai/gpt-4o-mini python examples/openrouter_api.py
```

Free models available at https://openrouter.ai/models?q=free.
If the API key is missing, the script falls back to mock automatically.

## Cognitive biases

```bash
python examples/cognitive_biases.py
```

Prints a step-by-step demo of each bias (ConfirmationBias, AvailabilityHeuristic,
AnchoringBias, RecencyBias) and runs a 30-tick simulation with `ENABLE_BIASES=true`.

## Custom scenario

```bash
python examples/custom_scenario.py
```

Template for defining your own world (POIs, layout), agents, and SimConfig.
Edit `build_party_world()` and `build_party_scenario()` to create your scenario.

## Next steps

- Full 100-tick benchmark: `python scripts/run_sim_100_ticks_blocking.py --preset blocking_balanced`
- Docker deployment: see [docs/guides/DOCKER.md](../docs/guides/DOCKER.md)
- Research layers (NEAT, HRM, RLIF, …): see [docs/research/LAYERS.md](../docs/research/LAYERS.md)
- Tutorial (Ollama + OpenRouter setup): see [docs/tutorials/GETTING_STARTED.md](../docs/tutorials/GETTING_STARTED.md)
