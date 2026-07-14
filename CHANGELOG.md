# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.1.0] — 2026-07-14

### Added
- Modular `gen_agent/` package with protocol-based interfaces (`SimProtocol`, `MemoryProtocol`, `StanfordAdapterProtocol`)
- `SimEngine` — tick-based simulation engine with proximity detection, mission system, and dialogue integration
- `DialogueEngine` — LLM-driven agent conversations with intent packs, emotion context, and retry/quality guards
- `MemoryManager` — dual-mode SQLite (dev) / PostgreSQL (prod) memory backend with Alembic migrations
- Memory decay, MaRS privacy engine, GraphRAG retriever, and FAISS vector store (all opt-in via env flags)
- Cognitive bias layer: `ConfirmationBias`, `AvailabilityHeuristic`, `AnchoringBias`
- Emotion model (`EmotionState`) with valence/arousal integrated into dialogue prompts
- Stanford Generative Agents reference code vendored under `reverie/` (not a git submodule)
- `StanfordAdapter` + async `StanfordCognitionWorker` for plan/reflect delegation
- Plan-to-POI matching with keyword fallback and alias table
- FastAPI server with WebSocket live dashboard (`web/index.html`)
- `structlog` structured logging throughout
- CI/CD: `ci.yml` (lint + mypy + unit + Postgres migration), `security.yml` (bandit + trivy + pip-audit), `cd.yml`
- 26 test files covering unit and integration scenarios; coverage gate at 70%
- `CITATION.cff`, `NOTICE`, `CONTRIBUTING.md` for open-source compliance
- Full English codebase — no Italian in code, comments, or documentation

### Architecture highlights vs legacy Gen_Agent
- SimEngine: ~760 lines vs ~1500+ in the monolithic legacy
- Memory: swappable backend protocol vs single coupled `UniversalMemoryManager` (~2300 lines)
- Stanford integration: optional adapter with explicit boundary rule vs always-active worker
- Dependencies: single `pyproject.toml` source of truth, no duplicate `requirements.txt`
