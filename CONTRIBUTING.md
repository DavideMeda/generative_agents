# Contributing to New Gen Agent

Thank you for your interest in contributing! This document explains the workflow for submitting changes.

## Getting started

```bash
git clone https://github.com/DavideMeda/new-gen-agent.git
cd new-gen-agent
pip install -e ".[dev]"
pre-commit install
```

## Running the test suite

```bash
pytest                    # unit tests (fast, no LLM required)
pytest tests/integration/ # requires running server or Postgres
```

Coverage gate: core modules must stay at or above 70%.

## Code style

- **Formatter:** `black` (line length 99)
- **Linter:** `ruff` (rules E, F, I, UP)
- **Types:** `mypy --strict` on `gen_agent/`

Run all checks at once:

```bash
ruff check gen_agent/ tests/ --fix
mypy gen_agent/ --ignore-missing-imports
```

Pre-commit runs these automatically on every commit.

## Branch strategy

See [.github/BRANCH_STRATEGY.md](.github/BRANCH_STRATEGY.md) for the full branching model.

Short version:

| Branch | Purpose |
|--------|---------|
| `main` | Stable, CI-green, always deployable |
| `feature/*` | New features — PR into `main` |
| `fix/*` | Bug fixes — PR into `main` |
| `research/*` | Experimental — may not be stable |

## Pull request checklist

- [ ] CI passes (lint + unit tests + mypy)
- [ ] New logic has at least one unit test
- [ ] No Italian text in comments or docstrings
- [ ] `NOTICE` updated if new third-party code is included
- [ ] Docs updated if public interface changes

## Reporting bugs

Open a GitHub Issue using the Bug Report template. Include:
- Python version and OS
- Exact command that failed
- Full traceback
- Relevant env vars (redact any API keys)

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
