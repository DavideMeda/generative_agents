# Architecture Diagrams

Visual overview of New Gen Agent's architecture using Mermaid diagrams.

---

## 1. System Overview

High-level components and data flow:

```mermaid
graph TB
    User[User/Client]
    API[FastAPI Server]
    WS[WebSocket Handler]
    Engine[SimEngine]
    Memory[MemoryManager]
    Dialogue[DialogueEngine]
    LLM[LLM Provider]
    DB[(PostgreSQL/SQLite)]
    Stanford[Stanford Adapter]
    
    User -->|HTTP/WS| API
    API --> WS
    WS -->|state updates| User
    API --> Engine
    Engine --> Memory
    Engine --> Dialogue
    Engine --> Stanford
    Dialogue --> LLM
    Memory --> DB
    Stanford -->|plan/POI| Engine
    
    style Engine fill:#c4f542,stroke:#333,color:#000
    style Memory fill:#00d9ff,stroke:#333,color:#000
    style LLM fill:#ff6b6b,stroke:#333,color:#fff
```

**Key components:**
- **FastAPI Server:** REST API + WebSocket for real-time updates
- **SimEngine:** Core tick-based simulation loop
- **MemoryManager:** Persistent agent memories with decay
- **DialogueEngine:** LLM-powered conversations
- **Stanford Adapter:** Integration with original Stanford codebase

---

## 2. SimEngine Tick Loop

What happens during a single `engine.advance()` call:

```mermaid
flowchart TD
    Start([Tick N])
    Increment[Increment tick counter]
    Stanford[Stanford: perceive + plan]
    POI[Plan → POI translation]
    Movement[Update agent positions]
    Proximity[Check proximity pairs]
    Interact{Within radius?}
    Dialogue[Run dialogue via DialogueEngine]
    Memories[Store memories]
    Optional[Apply optional layers]
    Events[Collect events]
    End([Return TickResult])
    
    Start --> Increment
    Increment --> Stanford
    Stanford --> POI
    POI --> Movement
    Movement --> Proximity
    Proximity --> Interact
    Interact -->|Yes| Dialogue
    Interact -->|No| Optional
    Dialogue --> Memories
    Memories --> Optional
    Optional --> Events
    Events --> End
    
    style Dialogue fill:#00d9ff,stroke:#333,color:#000
    style Memories fill:#c4f542,stroke:#333,color:#000
```

**Flow:**
1. Increment tick counter
2. Stanford: perceive environment, generate plan
3. Translate plan → POI (Plan-to-POI matching)
4. Update agent positions (move toward target POI)
5. Check proximity (find agents within `interaction_radius`)
6. Run dialogue if agents are close enough
7. Store memories for both agents
8. Apply optional layers (HRM, RLIF, SEAL, etc.)
9. Collect events and return `TickResult`

---

## 3. Memory System

How memories are stored, retrieved, and decayed:

```mermaid
flowchart LR
    Event[Event occurs]
    Create[Create Memory]
    Store[(SQLite/PostgreSQL)]
    Retrieve[Query memories]
    Decay[Apply decay engine]
    Score[Compute relevance score]
    Return[Return top-k memories]
    
    Event --> Create
    Create -->|INSERT| Store
    Retrieve -->|SELECT| Store
    Store --> Decay
    Decay --> Score
    Score --> Return
    
    subgraph Scoring
        Recency[Recency weight]
        Importance[Importance weight]
        Relevance[Keyword relevance]
        Score
    end
    
    Decay --> Recency
    Decay --> Importance
    Retrieve --> Relevance
    Recency --> Score
    Importance --> Score
    Relevance --> Score
    
    style Store fill:#00d9ff,stroke:#333,color:#000
    style Score fill:#c4f542,stroke:#333,color:#000
```

**Retrieval scoring formula:**

```
score = recency_weight * importance_weight * relevance_weight
```

- **Recency:** Exponential decay based on time since last access
- **Importance:** Agent-assigned salience (0.0–10.0)
- **Relevance:** Keyword overlap with query

---

## 4. Dialogue Flow

Agent-to-agent conversation generation:

```mermaid
sequenceDiagram
    participant Engine as SimEngine
    participant Dialogue as DialogueEngine
    participant Memory as MemoryManager
    participant LLM as LLM Provider
    
    Engine->>Dialogue: run(agent_a, agent_b, context)
    Dialogue->>Memory: retrieve(agent_a, query)
    Memory-->>Dialogue: relevant memories
    Dialogue->>Dialogue: build_intent_pack()
    Dialogue->>LLM: complete(prompt)
    LLM-->>Dialogue: utterance text
    Dialogue->>Dialogue: validate_utterance()
    alt Valid
        Dialogue->>Memory: add(agent_a, memory)
        Dialogue->>Dialogue: next turn
    else Invalid
        Dialogue->>LLM: retry with hints
    end
    Dialogue-->>Engine: Conversation
```

**Steps:**
1. Retrieve relevant memories for both agents
2. Build intent pack (goals, emotions, traits)
3. Generate prompt with scenario + memories + intent
4. LLM generates utterance
5. Validate (length, quality score, guards)
6. Store as memory
7. Repeat for N turns

---

## 5. Stanford Integration Boundary

How the new architecture interacts with vendored Stanford code:

```mermaid
graph TB
    subgraph New Gen Agent
        Engine[SimEngine]
        Adapter[StanfordAdapter]
        Memory[MemoryManager]
    end
    
    subgraph Stanford Vendored Code
        Persona[Persona]
        Scratch[Scratch]
        CognitiveModules[Cognitive Modules]
        PromptTemplates[Prompt Templates]
    end
    
    Engine --> Adapter
    Adapter -->|perceive| Persona
    Adapter -->|plan| CognitiveModules
    Persona --> Scratch
    CognitiveModules --> PromptTemplates
    Adapter -->|read plan| Scratch
    Adapter -->|translate to POI| Engine
    Memory -.->|optional| Persona
    
    style Adapter fill:#ff6b6b,stroke:#333,color:#fff
    style Engine fill:#c4f542,stroke:#333,color:#000
```

**Adapter responsibilities:**
- Wrap Stanford's `Persona` class
- Call `perceive()`, `plan()` methods
- Translate Stanford's textual plans → POI objects
- Isolate new codebase from Stanford internals

**Why vendored?**
- Stanford code is frozen (research artifact)
- No upstream changes expected
- Full control over modifications
- Simplifies testing and deployment

---

## 6. Optional Layers (Dependency Injection)

How optional layers are wired into `SimEngine`:

```mermaid
flowchart TD
    Factory[engine_factory.py]
    Flags{Environment variables}
    
    subgraph Cognitive Layers
        Biases[BiasLayer]
        HRM[HRMOrchestrator]
        RLIF[RLIFEngine]
        SEAL[SEALEnhancer]
    end
    
    subgraph Social Layers
        GameEngine[GameEngine]
        SocialLearning[KnowledgeDiffusion]
        Consensus[ConsensusEngine]
    end
    
    Engine[SimEngine]
    
    Factory --> Flags
    Flags -->|ENABLE_BIASES=true| Biases
    Flags -->|ENABLE_HRM=true| HRM
    Flags -->|ENABLE_RLIF=true| RLIF
    Flags -->|ENABLE_SEAL=true| SEAL
    Flags -->|ENABLE_GAME_THEORY=true| GameEngine
    Flags -->|ENABLE_SOCIAL_LEARNING=true| SocialLearning
    Flags -->|ENABLE_CONSENSUS=true| Consensus
    
    Biases --> Engine
    HRM --> Engine
    RLIF --> Engine
    SEAL --> Engine
    GameEngine --> Engine
    SocialLearning --> Engine
    Consensus --> Engine
    
    style Factory fill:#00d9ff,stroke:#333,color:#000
    style Engine fill:#c4f542,stroke:#333,color:#000
```

**Pattern:**
- All layers are **optional** (disabled by default)
- Enabled via environment variables (`ENABLE_*=true`)
- Injected into `SimEngine` constructor
- If `None`, layer is skipped (no performance cost)

---

## 7. LLM Provider Stack

Circuit breaker + provider abstraction:

```mermaid
graph TB
    Dialogue[DialogueEngine]
    CircuitBreaker[CircuitBreaker]
    Provider[LLMProvider]
    
    subgraph Implementations
        Ollama[OllamaProvider]
        OpenRouter[OpenRouterProvider]
        Anthropic[AnthropicProvider]
        Mock[MockProvider]
    end
    
    Dialogue --> CircuitBreaker
    CircuitBreaker -->|complete| Provider
    Provider -.->|Ollama| Ollama
    Provider -.->|OpenRouter| OpenRouter
    Provider -.->|Anthropic| Anthropic
    Provider -.->|Mock fallback| Mock
    
    CircuitBreaker -->|3 failures| OPEN[Circuit OPEN]
    OPEN -->|after timeout| HALF_OPEN[Circuit HALF_OPEN]
    HALF_OPEN -->|success| CLOSED[Circuit CLOSED]
    HALF_OPEN -->|failure| OPEN
    
    style CircuitBreaker fill:#ff6b6b,stroke:#333,color:#fff
    style Provider fill:#00d9ff,stroke:#333,color:#000
```

**Circuit breaker states:**
- **CLOSED:** Normal operation (calls pass through)
- **OPEN:** LLM unavailable (fail fast, return error)
- **HALF_OPEN:** Testing recovery (allow 1 call)

**Benefits:**
- Prevents cascade failures
- Graceful degradation (fall back to mock)
- Automatic recovery after timeout

---

## 8. Database Schema

Core tables and relationships:

```mermaid
erDiagram
    MEMORIES {
        int id PK
        string agent_id
        string content
        float importance
        int tick_created
        float last_accessed
        string tags
    }
    
    REFLECTIONS {
        int id PK
        string agent_id
        string insight
        int tick_created
        string evidence_ids
    }
    
    AGENTS {
        string agent_id PK
        string name
        float pos_x
        float pos_y
        json traits
        int last_tick
    }
    
    SIMULATIONS {
        int id PK
        string scenario_name
        int tick_count
        timestamp started_at
        timestamp ended_at
    }
    
    MEMORIES ||--o{ AGENTS : belongs_to
    REFLECTIONS ||--o{ AGENTS : belongs_to
    AGENTS ||--o{ SIMULATIONS : participates_in
```

**Tables:**
- **memories:** Per-agent event/observation storage
- **reflections:** LLM-generated insights (higher-order memories)
- **agents:** Agent state (position, traits, last tick)
- **simulations:** Metadata for simulation runs

**Migrations:** Managed by Alembic (`migrations/versions/`)

---

## 9. WebSocket Real-time Updates

Server-to-client message flow:

```mermaid
sequenceDiagram
    participant Client as Browser (WebSocket)
    participant Server as FastAPI Server
    participant Engine as SimEngine
    participant Broadcast as ConnectionManager
    
    Client->>Server: ws://localhost:8000/ws
    Server->>Broadcast: register(connection)
    Server-->>Client: {"type": "connected"}
    
    loop Every tick
        Engine->>Engine: advance()
        Engine->>Broadcast: notify(TickResult)
        Broadcast->>Client: {"type": "tick_update", "tick": N, ...}
        Broadcast->>Client: {"type": "agent_moved", "agent_id": "a1", ...}
        Broadcast->>Client: {"type": "interaction", "agents": [...], ...}
    end
    
    Client->>Server: disconnect
    Server->>Broadcast: unregister(connection)
```

**Message types:**
- `connected`: Initial handshake
- `tick_update`: New tick + global stats
- `agent_moved`: Agent position update
- `interaction`: Agents met and interacted
- `dialogue`: Conversation utterances
- `error`: Simulation error or warning

**Protocol:** See [`docs/guides/WEBSOCKET_PROTOCOL.md`](../guides/WEBSOCKET_PROTOCOL.md)

---

## 10. CI/CD Pipeline

GitHub Actions workflow:

```mermaid
flowchart LR
    Push[git push]
    Lint[Lint: ruff + mypy]
    Test[Test: pytest]
    Coverage[Coverage: 70%+ gate]
    Docker[Docker: build image]
    Deploy[Deploy: GH Pages]
    
    Push --> Lint
    Lint --> Test
    Test --> Coverage
    Coverage --> Docker
    Docker --> Deploy
    
    Lint -->|failure| Fail[❌ CI failed]
    Test -->|failure| Fail
    Coverage -->|< 70%| Fail
    Docker -->|failure| Fail
    
    style Coverage fill:#c4f542,stroke:#333,color:#000
    style Deploy fill:#00d9ff,stroke:#333,color:#000
    style Fail fill:#ff6b6b,stroke:#333,color:#fff
```

**Jobs:**
1. **Lint:** `ruff` (E, F, I, UP rules) + `mypy --strict`
2. **Test:** `pytest` on Python 3.10 + 3.11
3. **Coverage:** Enforce 70%+ on `gen_agent/`
4. **Postgres:** Integration tests with PostgreSQL service
5. **Smoke:** Run `hello_world.py` + 10-tick mock sim
6. **Docker:** Build multi-stage image + health check
7. **Pages:** Deploy Astro site to GitHub Pages

**Triggers:** Push to `main`/`develop`, pull requests

---

## Color Legend

```mermaid
graph LR
    Core[Core component]
    Storage[Storage/Database]
    External[External service]
    Optional[Optional layer]
    
    style Core fill:#c4f542,stroke:#333,color:#000
    style Storage fill:#00d9ff,stroke:#333,color:#000
    style External fill:#ff6b6b,stroke:#333,color:#fff
    style Optional fill:#333,stroke:#666,color:#fff
```

---

## See also

- [OVERVIEW.md](OVERVIEW.md) — Textual architecture description
- [MODULARITY.md](MODULARITY.md) — Protocol-based design patterns
- [UPSTREAM_RELATIONSHIP.md](UPSTREAM_RELATIONSHIP.md) — Stanford fork details
- [../guides/WEB_UI.md](../guides/WEB_UI.md) — WebSocket API details
- [../database/SCHEMA.md](../database/SCHEMA.md) — Full database schema
