# Getting Started — Your First Simulation

Walks you through running your first simulation using a local LLM (Ollama),
a cloud API (OpenRouter), or no LLM at all (mock).

## Prerequisites

- Python 3.10+
- Git

## Installation

```bash
git clone https://github.com/DavideMeda/new-gen-agent.git
cd new-gen-agent
pip install -e ".[dev]"
```

---

## Step 1 — Quick offline test

Confirm the install works — no LLM, no network:

```bash
python examples/hello_world.py
```

Expected output (numbers may vary):

```
=== hello_world — 3 agents, 10 ticks, mock LLM ===

  tick  5  interaction: Alice & Bob
  tick  9  interaction: Bob & Carol

--- Final stats after 10 ticks ---
  Interactions : 2
  Dialogues    : 2
  Memories     : 12
  Final tick   : 10
```

---

## Option A — Local LLM with Ollama

Ollama runs models on your machine — no API key, no data sent to the cloud.

### Install Ollama

- **Windows / macOS:** Download from https://ollama.com
- **Linux:** `curl -fsSL https://ollama.com/install.sh | sh`

### Pull a model

```bash
ollama pull llama3.2:3b        # 2 GB — fast, good starting point
ollama pull llama3.1:8b        # 5 GB — better quality
```

### Verify it works

```bash
ollama run llama3.2:3b "Say hello in one word"
# Expected: Hello  (within a few seconds)
```

If this hangs, restart Ollama (tray icon → Quit → reopen).

### Run a simulation

```bash
python examples/ollama_simple.py

# Or with the benchmark script:
python scripts/run_sim_100_ticks_blocking.py --preset fast --ticks 20 --llm ollama
```

### Use a different model

```bash
# Linux / macOS
OLLAMA_MODEL=llama3.1:8b python examples/ollama_simple.py

# Windows
set OLLAMA_MODEL=llama3.1:8b
python examples/ollama_simple.py
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `HTTP Error 500` | Restart Ollama (tray → Quit → reopen) |
| `[pre-flight] Falling back to mock` | Ollama not responding — check it runs with `ollama list` |
| Very slow (>5 min/tick) | Model too large for your RAM — use `llama3.2:3b` |

The script includes a **pre-flight check**: if Ollama is unreachable it falls back
to mock automatically so the simulation still completes.

---

## Option B — Cloud API with OpenRouter

OpenRouter provides access to many models (including free tiers) via one API key.
No local GPU required.

### Get a free API key

1. Sign up at https://openrouter.ai
2. Go to **API Keys** → **Create Key** (no credit card needed for free models)

### Free models

| Model slug | Notes |
|-----------|-------|
| `qwen/qwen3-235b-a22b:free` | Default — good quality |
| `meta-llama/llama-3.2-3b-instruct:free` | Fast |
| `mistralai/mistral-7b-instruct:free` | Balanced |

Full list: https://openrouter.ai/models?q=free

### Run a simulation

```bash
# Linux / macOS
export OPENROUTER_API_KEY=sk-or-...
python examples/openrouter_api.py

# Windows
set OPENROUTER_API_KEY=sk-or-...
python examples/openrouter_api.py

# Custom model
OPENROUTER_MODEL=openai/gpt-4o-mini python examples/openrouter_api.py
```

Or with the benchmark script:

```bash
export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY=sk-or-...
python scripts/run_sim_100_ticks_blocking.py --preset fast --ticks 20
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `[OpenRouter error 401]` | API key missing or wrong |
| `[OpenRouter error 429]` | Rate limited — wait 60 s |
| `[OpenRouter error 503]` | Model overloaded — try another free model |

---

## Option C — Mock LLM (fully offline)

Generates placeholder phrases instantly — useful for testing and CI.

```bash
LLM_PROVIDER=mock python scripts/run_sim_100_ticks_blocking.py --preset fast --ticks 20
```

---

## Understanding the output

```
[pre-flight] OK — response: 'hello'
[tick  10] dialogue ['Giovanni', 'Elena'] turns=2 elapsed=12.4s
[PROGRESS] tick 10/50 | interactions=1 dialogues=1 missions_done=3
=== RESULT ===
dialogues: 4
memories_total: 48
reflections_generated: 6
real_time_sec: 142.8
llm_metrics: {circuit_state: CLOSED}
```

| Field | Meaning |
|-------|---------|
| `dialogues` | Completed LLM conversations |
| `memories_total` | Observations + reflections stored |
| `reflections_generated` | Higher-order memories synthesised by the LLM |
| `circuit_state` | `CLOSED`=healthy, `OPEN`=LLM down, `HALF_OPEN`=recovering |

Reports are saved to `output/` as JSON.

---

## Next steps

- More examples: `examples/` folder (biases, custom scenarios, OpenRouter)
- Web dashboard: `uvicorn server.main:app` then open `http://localhost:8000`
- Docker deployment: [docs/guides/DOCKER.md](../guides/DOCKER.md)
- Research layers (NEAT, HRM, biases): [docs/research/LAYERS.md](../research/LAYERS.md)
- Custom scenario: [examples/custom_scenario.py](../../examples/custom_scenario.py)
