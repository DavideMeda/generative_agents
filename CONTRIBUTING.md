# Contributing

## Before you start

1. Read the [Developer Onboarding](docs/guides/DEVELOPER_ONBOARDING.md) guide.
2. Read the [Branch Strategy](.github/BRANCH_STRATEGY.md).
3. Make sure tests pass locally: `pytest`.

## Workflow

1. **Open an issue** describing what you want to add or fix.
2. **Branch from `develop`**: `git checkout -b feature/your-feature develop`.
3. **Write tests first** (or at minimum alongside the code).
4. **Keep PRs small** — one logical change per PR.
5. **Open PR against `develop`** — never directly against `main`.

## Code standards

- Formatter: `black` (line length 99).
- Linter: `ruff`.
- Type hints: required for all public functions.
- Comments: explain *why*, not *what*.

Run before committing:

```bash
ruff check gen_agent/ tests/
mypy gen_agent/
pytest
```

## Boundary rule

> **Never import `reverie.*` outside of `gen_agent/integrations/stanford/adapter.py`.**

Violations will be rejected in code review.

## Syncing with Stanford upstream

Open a PR monthly (or when Stanford releases a relevant update):

```bash
git fetch upstream
git checkout develop
git merge upstream/main --no-ff -m "chore: sync upstream Stanford"
```

Resolve conflicts in `reverie/` and `environment/` — never change those files for Gen_Agent features.

## Commit message format

```
<type>: <short description>   (max 72 chars)

Types: feat, fix, refactor, docs, chore, test, style, ci
```
