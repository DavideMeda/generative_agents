# Research Layers

These modules extend the core simulation with experimental cognitive and social mechanisms.
They are **opt-in** (disabled by default) and **not covered by the CI test gate**.
Each layer is activated by setting the corresponding environment variable.

> All layers can be combined freely. Start with one at a time to understand its effect.

---

## Cognitive layers (`gen_agent/cognitive/`)

### HRM — Hierarchical Role Management
**File:** `gen_agent/cognitive/hrm.py`  
**Enable:** `ENABLE_HRM=true`

Assigns each agent a role (leader / mediator / observer / member) based on their Big Five traits.
Roles influence mission priority and interaction cooldowns.

### RLIF — Reinforcement Learning from Interaction Feedback
**File:** `gen_agent/cognitive/rlif.py`  
**Enable:** `ENABLE_RLIF=true`

After each interaction, updates a per-agent-pair reward signal.
Dynamically adjusts proximity radius and cooldown gaps so agents seek or avoid each other
based on the history of their interactions.

### SEAL — Social Emotional Adaptation Layer
**File:** `gen_agent/cognitive/seal.py`  
**Enable:** `ENABLE_SEAL=true`

Slowly shifts Big Five trait values based on accumulated interaction outcomes,
simulating long-term personality plasticity.

### Evolutionary Learning (SocialLearner + IntrinsicMotivation)
**File:** `gen_agent/cognitive/evolutionary.py`  
**Enable:** `ENABLE_SOCIAL_LEARNING=true`

Agents with lower cumulative reward copy traits from higher-reward agents (social imitation).
Agents also earn intrinsic reward for visiting new POIs (exploration bonus).

### BiasLayer — Cognitive Biases
**File:** `gen_agent/cognitive/biases.py`  
**Enable:** `ENABLE_BIASES=true`

Applies three psychological biases to interaction probability and dialogue intent:
- **ConfirmationBias** — agents prefer interacting with agents who share similar traits
- **AvailabilityHeuristic** — recent events inflate estimated interaction probability
- **AnchoringBias** — first computed probability anchors subsequent adjustments

---

## Social layers (`gen_agent/social/`)

### GameEngine — Game Theory
**File:** `gen_agent/social/game_theory.py`  
**Enable:** `ENABLE_GAME_THEORY=true`

Models agent interactions as 2-player games (Prisoner's Dilemma, Stag Hunt).
Nash equilibrium solver for pure-strategy 2×2 payoff matrices.
Outcomes feed into RLIF to update reward signals.

### Social Learning (ImitationEngine + KnowledgeDiffusion)
**File:** `gen_agent/social/social_learning.py`  
**Enable:** `ENABLE_SOCIAL_LEARNING=true`

Agents with lower reward copy strategies from higher-reward agents.
"Public" memories propagate between agents who meet, simulating gossip and shared knowledge.

### ConsensusEngine — Collective Decision-Making
**File:** `gen_agent/social/consensus.py`  
**Enable:** `ENABLE_CONSENSUS=true`

Runs group decisions using majority vote, Borda count, or iterative Delphi rounds.
Useful for scenarios where agents must reach a collective agreement.

---

## Advanced memory layers (`gen_agent/memory/`)

| Layer | File | Enable flag |
|---|---|---|
| GraphRAG retriever | `memory/graph/graphrag_retriever.py` | `ENABLE_GRAPHRAG=true` |
| MaRS privacy engine | `memory/privacy/mars_engine.py` | `ENABLE_MARS=true` |
| Memory compressor | `memory/compression/compressor.py` | `ENABLE_MEMORY_COMPRESSION=true` |
| FAISS vector store | `memory/vector/faiss_store.py` | `ENABLE_VECTOR_MEMORY=true` |

---

## NEAT evolution (`gen_agent/training/neat/`)

**Enable:** `ENABLE_NEAT=true`

Evolves agent movement and decision policies using the NEAT algorithm (NeuroEvolution of
Augmenting Topologies). Requires `numpy`. Population and genomes are persisted to disk.

---

## Status summary

| Layer | CI tested | Coverage gate |
|---|---|---|
| BiasLayer | Yes | No (omitted) |
| HRM | No | No |
| RLIF | No | No |
| SEAL | No | No |
| Evolutionary | No | No |
| GameEngine | No | No |
| Social Learning | No | No |
| ConsensusEngine | No | No |
| GraphRAG | No | No |
| MaRS | No | No |
| Memory compressor | No | No |
| FAISS | No | No |
| NEAT | No | No |
