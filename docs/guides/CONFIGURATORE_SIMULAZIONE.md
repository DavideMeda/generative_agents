# Simulation Configuration Guide

## Quick Start: Preset-Based Launch

```bash
# Run with the default blocking_balanced preset (100 ticks, 5 agents, Ollama)
python scripts/run_sim_100_ticks_blocking.py --preset blocking_balanced --llm ollama

# Fast offline test (no LLM)
python scripts/run_sim_100_ticks_blocking.py --preset fast --llm mock
```

## Available Presets

| Preset | Ticks | Agents | Blocking | Notes |
|--------|-------|--------|----------|-------|
| `fast` | 20 | 3 | No | Quick smoke test |
| `blocking_balanced` | 100 | 5 | Yes | Legacy parity target |
| `dense_100` | 100 | 8 | No | High interaction density |
| `complex` | 200 | 10 | No | All layers enabled |
| `long` | 500 | 5 | Yes | Extended run |

## Custom Profile

Copy the example and edit:
```bash
cp config/user_simulation_profile.example.json config/user_simulation_profile.json
```

The profile is loaded automatically when you run the simulation script.
Any field in the profile overrides the preset default.

## Feature Flags

Override individual layers via environment variables:

```bash
ENABLE_STANFORD_WORKER=1 ENABLE_GAME_THEORY=1 \
  python scripts/run_sim_100_ticks_blocking.py --preset blocking_balanced
```

## launch_profile API

```python
from config.launch_profile import load_profile, apply_profile_to_env

profile = load_profile("blocking_balanced")
profile.ticks = 50      # override
apply_profile_to_env(profile)
```
