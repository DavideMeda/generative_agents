# Architecture Overview

## Design philosophy

Gen_Agent is built **on top of** the Stanford Generative Agents fork, not alongside it.
All Gen_Agent code lives in the `gen_agent/` Python namespace.
Stanford code (`reverie/`, `environment/`) is treated as a read-only upstream dependency.

## Layered architecture

```
┌─────────────────────────────────────────┐
│            Application Layer            │
│  server/ (HTTP API)  │  scripts/        │
├─────────────────────────────────────────┤
│           Gen_Agent Core Layer          │
│  sim/  │  memory/  │  dialogue/  │  telemetry/ │
├─────────────────────────────────────────┤
│           Interface (Protocol) Layer    │
│  MemoryProtocol  SimProtocol  StanfordAdapterProtocol │
├─────────────────────────────────────────┤
│         Stanford Integration Layer      │
│  gen_agent/integrations/stanford/       │  ← ONLY here imports reverie/
├─────────────────────────────────────────┤
│             Stanford Upstream           │
│  reverie/   environment/                │  ← read-only, never modified
└─────────────────────────────────────────┘
```

## Boundary rule

> **Only `gen_agent/integrations/stanford/adapter.py` is allowed to import from `reverie/`.**

This is enforced by code review. If you need data from the Stanford layer, add a method to `StanfordAdapterProtocol` and implement it in the adapter — never import Stanford modules directly from `gen_agent/sim/` or `gen_agent/memory/`.

## Module responsibilities

| Module | Responsibility |
|--------|---------------|
| `gen_agent/interfaces/` | Stable contracts (Protocols). Never import from implementations. |
| `gen_agent/memory/` | Memory CRUD, decay scoring, SQLite persistence |
| `gen_agent/sim/` | Tick loop, agent registration, proximity detection |
| `gen_agent/dialogue/` | LLM-driven agent conversations |
| `gen_agent/telemetry/` | Metrics recording and report generation |
| `gen_agent/integrations/stanford/` | Bridge to Stanford plan/reflect/scratch APIs |

## Data flow (one tick)

```
SimEngine.advance()
    → ProximityDetector.detect_pairs()
    → StanfordAdapter.run_agent_plan()   [optional]
    → MemoryManager.store(observation)
    → TelemetryReporter.record(tick_result)
    → TickResult returned to caller
```

## Extending the system

- **New memory type**: add to `Memory.memory_type` allowed values + one Alembic migration.
- **New LLM backend**: implement `LLMCallable` signature and pass to `DialogueEngine`.
- **New storage backend**: implement `MemoryProtocol` and inject into `MemoryManager`.
- **New Stanford feature**: add method to `StanfordAdapterProtocol`, implement in `adapter.py`.
