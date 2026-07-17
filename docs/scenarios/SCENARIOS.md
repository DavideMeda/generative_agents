# Built-in Scenarios

All scenarios live in `scenarios/` and are loadable via `load_scenario("name")`.

```python
from config.scenario import load_scenario
scenario = load_scenario("offline")
engine = scenario.build_engine()
```

---

## Available scenarios

### `blocking_100`

**File:** `scenarios/blocking_100.py`  
**Agents:** 5 (Marco, Lucia, Giovanni, Anna, Elena)  
**LLM:** Ollama (default) or OpenRouter  
**Features:** Blocking dialogues, Stanford cognition worker, POI missions, plan-to-POI matching  
**Use case:** Primary benchmark — matches the legacy Gen_Agent parity target

```bash
python scripts/run_sim_100_ticks_blocking.py --preset blocking_balanced --llm ollama
python scripts/run_sim_100_ticks_blocking.py --preset blocking_balanced --llm mock
```

---

### `debate`

**File:** `scenarios/debate.py`  
**Agents:** 3 (Sophia, Marcus, Lena)  
**LLM:** Mock (fast by default)  
**Features:** Large interaction radius (agents always find each other), 8-turn dialogues, no missions  
**Use case:** Testing consensus and social learning modules; high-frequency dialogue benchmarks

```python
from scenarios.debate import SCENARIO
from config.engine_factory import build_sim_engine

engine, _ = build_sim_engine(SCENARIO)
for _ in range(30):
    engine.advance()
print(engine.stats())
```

Or quickly from CLI:

```bash
python -c "
from scenarios.debate import SCENARIO
from config.engine_factory import build_sim_engine
engine, _ = build_sim_engine(SCENARIO)
[engine.advance() for _ in range(30)]
print(engine.stats())
"
```

---

### `offline`

**File:** `scenarios/offline.py`  
**Agents:** 5 (Alice, Bob, Carol, David, Eve)  
**LLM:** Mock (no network calls)  
**Features:** Full world + POI missions + mock dialogue, instant tick progression  
**Use case:** CI smoke tests, profiling, stress testing without any LLM dependency

```python
from scenarios.offline import SCENARIO
from config.engine_factory import build_sim_engine

engine, _ = build_sim_engine(SCENARIO)
for _ in range(50):
    engine.advance()
print(engine.stats())
```

---

### `default`

**File:** `scenarios/default.py`  
**Agents:** 5 (Alice, Bob, Carol, David, Eve)  
**LLM:** Ollama  
**Features:** Balanced config with Stanford worker enabled; 1-second tick interval  
**Use case:** General-purpose template — copy and customise for your own scenario

```python
from config.scenario import load_scenario
scenario = load_scenario("default")
engine = scenario.build_engine()
for _ in range(20):
    engine.advance()
```

---

## Creating your own scenario

Use `examples/custom_scenario.py` as a starting template.
Key parameters to configure in `SimConfig`:

| Parameter | Effect |
|-----------|--------|
| `interaction_radius` | Distance (units) within which two agents can interact |
| `min_gap_ticks` | Minimum ticks between two interactions for the same pair |
| `block_on_dialogue` | If True, engine waits for LLM response before advancing |
| `dialogue_max_turns` | Maximum utterances per conversation |
| `missions_enabled` | Whether agents receive visit-POI goals |
| `mission_duration_ticks` | How long an agent pursues a mission before getting a new one |
| `seed` | RNG seed for reproducible runs |

### Alternative: build from a LaunchProfile preset

```python
from config.launch_profile import load_profile
from config.scenario import Scenario

scenario = Scenario.from_profile(load_profile("fast"))
engine = scenario.build_engine()
```

Available presets: `fast`, `blocking_balanced`, `dense_100`, `complex`, `long`.  
See `config/launch_profile.py` for their full definitions.
