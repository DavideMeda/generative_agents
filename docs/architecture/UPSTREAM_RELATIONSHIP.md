# Upstream Relationship: Stanford Generative Agents

## Overview

`Nuovo Gen_Agent` is a **fork** of Stanford Generative Agents (git `upstream` =
`joonspk-research/generative_agents`). The Stanford reference code is **vendored**
under `reverie/` (copied into the repo, *not* a git submodule — there is no
`.gitmodules` and no nested `.git`, so there is no "repo inside a repo").
The project does **not** inherit from it structurally. The relationship is:

- `reverie/` lives at the project root as a vendored reference implementation.
- The project's own simulation engine (`gen_agent/sim/engine.py`) is written
  independently, with Stanford cognition injected optionally via an adapter.
- `upstream` can be re-synced periodically (see `.github/BRANCH_STRATEGY.md`).

## Integration Points

| Our module | Stanford equivalent | Notes |
|-----------|---------------------|-------|
| `gen_agent/integrations/stanford/adapter.py` | `reverie/reverie.py` | Adapts plan/reflect to our interfaces |
| `gen_agent/integrations/stanford/cognitive.py` | `reverie/ga/persona/persona.py` | Slim bridge (no full Persona dependency) |
| `gen_agent/integrations/stanford/plan_to_poi.py` | Internal Stanford plan → tile logic | Ported, simplified |
| `gen_agent/integrations/stanford/worker.py` | `core/stanford_cognition_worker.py` | Background thread worker |

## Boundary Rule

Only `gen_agent/integrations/stanford/` may import from `reverie/`.
This isolates the Stanford dependency: removing it does not break the rest of the system.

## Phase 2: Full Persona Integration (optional, future)

To use real `reverie.Persona` objects:
1. Extend `cognitive.py` to bootstrap `Persona` from reverie.
2. Route planning and reflection through the real Persona instance.
3. Keep the adapter interface unchanged so no other code needs to change.
