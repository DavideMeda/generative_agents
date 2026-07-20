# Building a Custom Cognitive Layer

This tutorial shows how to add a new cognitive layer to New Gen Agent.

**Example:** We'll build a `FatigueLayer` that tracks agent tiredness and reduces interaction probability when an agent is exhausted.

---

## Step 1: Define the layer interface

Create `gen_agent/cognitive/fatigue.py`:

```python
"""FatigueLayer — tracks agent tiredness and modulates interaction willingness."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FatigueState:
    """Per-agent fatigue state."""
    agent_id: str
    energy: float = 100.0          # 0.0 = exhausted, 100.0 = full energy
    last_rest_tick: int = 0


class FatigueLayer:
    """
    Fatigue accumulates with each interaction and movement.
    When energy < 20, interaction probability is halved.
    Agents recover 5 energy per tick when idle.
    """

    def __init__(self, decay_per_tick: float = 1.0, recovery_per_tick: float = 5.0) -> None:
        self._decay = decay_per_tick
        self._recovery = recovery_per_tick
        self._states: dict[str, FatigueState] = {}

    def register_agent(self, agent_id: str) -> None:
        """Register a new agent with full energy."""
        if agent_id not in self._states:
            self._states[agent_id] = FatigueState(agent_id=agent_id)

    def on_interaction(self, agent_id: str, current_tick: int) -> None:
        """Agent participated in an interaction — reduce energy by 10."""
        state = self._states.get(agent_id)
        if state:
            state.energy = max(0.0, state.energy - 10.0)

    def on_tick(self, agent_id: str, current_tick: int, was_idle: bool) -> None:
        """Called every tick — decay or recover energy."""
        state = self._states.get(agent_id)
        if not state:
            return
        
        if was_idle:
            # Idle agents recover energy
            state.energy = min(100.0, state.energy + self._recovery)
            state.last_rest_tick = current_tick
        else:
            # Active agents lose energy
            state.energy = max(0.0, state.energy - self._decay)

    def interaction_multiplier(self, agent_id: str) -> float:
        """
        Return a multiplier for interaction probability.
        
        If energy < 20: multiplier = 0.5 (tired, avoid interactions)
        If energy >= 20: multiplier = 1.0 (normal)
        """
        state = self._states.get(agent_id)
        if not state:
            return 1.0
        return 0.5 if state.energy < 20.0 else 1.0

    def get_energy(self, agent_id: str) -> float:
        """Get current energy level for an agent."""
        state = self._states.get(agent_id)
        return state.energy if state else 100.0
```

---

## Step 2: Integrate into `SimEngine`

Edit `gen_agent/sim/engine.py`:

### 2.1 Add import and type hint

```python
if TYPE_CHECKING:
    from gen_agent.cognitive.fatigue import FatigueLayer  # new
```

### 2.2 Add field to `SimEngine.__init__()`

```python
def __init__(
    self,
    config: SimConfig,
    ...
    fatigue_layer: FatigueLayer | None = None,  # new
) -> None:
    ...
    self._fatigue = fatigue_layer
```

### 2.3 Register agents with the layer

In `register_agent()`:

```python
def register_agent(self, config: AgentConfig) -> str:
    ...
    if self._fatigue:
        self._fatigue.register_agent(agent_id)
    ...
```

### 2.4 Apply fatigue during interaction checks

In `_run_interaction()`:

```python
def _run_interaction(self, ...):
    ...
    base_prob = 0.8  # baseline interaction probability
    
    # Apply fatigue multiplier
    if self._fatigue:
        for aid in agent_ids:
            base_prob *= self._fatigue.interaction_multiplier(aid)
    
    if random.random() < base_prob:
        # interaction happens
        ...
        if self._fatigue:
            for aid in agent_ids:
                self._fatigue.on_interaction(aid, self._tick)
```

### 2.5 Update fatigue every tick

In `advance()`:

```python
def advance(self) -> TickResult:
    ...
    if self._fatigue:
        for aid, state in self._agents.items():
            was_idle = (state.target_poi is None)
            self._fatigue.on_tick(aid, self._tick, was_idle)
    ...
```

---

## Step 3: Wire via `engine_factory.py`

Edit `config/engine_factory.py`:

### 3.1 Add flag check

```python
def build_sim_engine(scenario: Scenario) -> tuple[SimEngine, EngineExtras]:
    ...
    enable_fatigue = _env_bool("ENABLE_FATIGUE", False)
    ...
```

### 3.2 Instantiate the layer

```python
    fatigue_layer = None
    if enable_fatigue:
        from gen_agent.cognitive.fatigue import FatigueLayer
        fatigue_layer = FatigueLayer(decay_per_tick=1.0, recovery_per_tick=5.0)
```

### 3.3 Pass to `SimEngine`

```python
    engine = SimEngine(
        config=cfg,
        ...
        fatigue_layer=fatigue_layer,
    )
```

---

## Step 4: Enable and test

Set the environment variable:

```bash
export ENABLE_FATIGUE=true
python examples/ollama_simple.py
```

**Expected behavior:**
- Agents with low energy (< 20) interact less frequently
- Idle agents recover energy over time
- Active agents gradually tire and reduce interaction rate

---

## Step 5: Add unit tests

Create `tests/unit/cognitive/test_fatigue.py`:

```python
"""Unit tests for FatigueLayer."""
from gen_agent.cognitive.fatigue import FatigueLayer


def test_register_agent_starts_with_full_energy():
    layer = FatigueLayer()
    layer.register_agent("a1")
    assert layer.get_energy("a1") == 100.0


def test_interaction_reduces_energy():
    layer = FatigueLayer()
    layer.register_agent("a1")
    layer.on_interaction("a1", current_tick=1)
    assert layer.get_energy("a1") == 90.0  # 100 - 10


def test_idle_tick_recovers_energy():
    layer = FatigueLayer(recovery_per_tick=5.0)
    layer.register_agent("a1")
    layer.on_interaction("a1", current_tick=1)  # energy = 90
    layer.on_tick("a1", current_tick=2, was_idle=True)  # +5
    assert layer.get_energy("a1") == 95.0


def test_active_tick_decays_energy():
    layer = FatigueLayer(decay_per_tick=2.0)
    layer.register_agent("a1")
    layer.on_tick("a1", current_tick=1, was_idle=False)  # -2
    assert layer.get_energy("a1") == 98.0


def test_low_energy_reduces_interaction_multiplier():
    layer = FatigueLayer()
    layer.register_agent("a1")
    # Reduce energy below 20
    for _ in range(9):
        layer.on_interaction("a1", current_tick=1)
    assert layer.get_energy("a1") < 20.0
    assert layer.interaction_multiplier("a1") == 0.5


def test_normal_energy_keeps_full_multiplier():
    layer = FatigueLayer()
    layer.register_agent("a1")
    assert layer.interaction_multiplier("a1") == 1.0
```

Run tests:

```bash
pytest tests/unit/cognitive/test_fatigue.py -v
```

---

## Step 6: Document the layer

Add entry to `docs/research/LAYERS.md`:

```markdown
### FatigueLayer — Energy Management
**File:** `gen_agent/cognitive/fatigue.py`  
**Enable:** `ENABLE_FATIGUE=true`

Tracks agent tiredness. Energy decreases with interactions and movement, recovers during idle ticks.
When energy < 20, interaction probability is halved. Simulates realistic social stamina.
```

---

## Best practices

1. **Naming:** Use descriptive class names ending in `Layer` or `Engine` (e.g., `FatigueLayer`, `EmotionEngine`)
2. **Protocol:** Define clear hooks: `on_interaction()`, `on_tick()`, `register_agent()`
3. **State isolation:** Store per-agent state in a dict keyed by `agent_id`
4. **Fail-safe:** Return neutral values (1.0 multiplier, 0.0 score) if agent not found
5. **Testing:** Write unit tests covering all public methods and edge cases
6. **Documentation:** Add to `LAYERS.md` with enable flag and brief description

---

## Next steps

- Add visualization: export fatigue data to WebSocket updates
- Combine with other layers: low energy + high neuroticism → avoid interactions
- Calibration: run benchmarks to tune `decay_per_tick` and `recovery_per_tick`

See also:
- `gen_agent/cognitive/biases.py` — reference implementation
- `gen_agent/sim/engine.py` — integration points
- `config/engine_factory.py` — wiring pattern
