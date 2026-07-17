# Roadmap

Planned features and improvements for `new-gen-agent`.
Items are loosely ordered by priority within each quarter.

## Q3 2026

- [ ] **Multi-scenario benchmarking suite** — automated comparison across `debate`, `party_planning`, `office` scenarios with a single command
- [ ] **FAISS embeddings for memory retrieval** — replace keyword-overlap relevance with vector cosine similarity (currently marked `ponytail:` in `decay_engine.py`)
- [ ] **Memory compression pipeline** — auto-consolidate old memories after N ticks to keep agent context lean in long simulations
- [ ] **Screenshot / demo GIF** — visual demo of the live WebSocket dashboard in `README.md`

## Q4 2026

- [ ] **Spatial canvas with A\* pathfinding** — replace straight-line movement with obstacle-aware navigation (rooms, doors, corridors)
- [ ] **Long-term simulations (1000+ ticks)** — checkpoint/resume support so multi-day studies can survive restarts
- [ ] **Agent-authored multi-day schedules** — plans that span across ticks ("host a dinner party on Friday") rather than single visit-POI goals
- [ ] **spaCy NER for knowledge graph** — replace naive entity extraction in `knowledge_graph.py` with proper named-entity recognition

## 2027

- [ ] **Multi-world federation** — agents can travel between independent world instances
- [ ] **Community scenario gallery** — curated collection of contributed scenarios with documented expected outputs
- [ ] **Nightly benchmark CI job** — automated overnight simulation run with regression alerts on key metrics (dialogues/tick, memories/tick)

## Completed

- [x] Modular architecture (engine, memory, dialogue, Stanford adapter decoupled)
- [x] Dual-mode storage (SQLite dev / PostgreSQL prod)
- [x] FastAPI + WebSocket live dashboard
- [x] CI/CD: lint + mypy + unit tests + security scan + Docker build
- [x] Code coverage gate ≥ 70%
- [x] Full English codebase (no Italian in code, comments, or docs)
- [x] Circuit breaker for LLM resilience
- [x] Getting started tutorial (Ollama + OpenRouter)
- [x] `examples/` folder with ready-to-run scripts

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) to work on any of these items.
Open an issue first to discuss approach before submitting a large PR.
