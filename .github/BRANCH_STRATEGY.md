# Branch Strategy — Gen_Agent (fork-first)

## Permanent branches

| Branch  | Purpose                                 | Protection |
|---------|-----------------------------------------|------------|
| `main`  | Stable, production-ready code           | Yes — PR + green CI required |
| `develop` | Continuous integration of features/fixes | Yes — PR + green CI required |

## Temporary branches (naming)
```
feature/<short-desc>   # new feature
refactor/<module>      # internal refactor
fix/<bug-desc>         # bugfix
docs/<topic>           # docs only
chore/<task>           # maintenance, deps, config
```

## Standard workflow
1. Branch from `develop`: `git checkout -b feature/my-feature develop`
2. Develop + test locally.
3. Open PR to `develop` — CI must be green.
4. Code review required (≥1 reviewer).
5. Squash merge into `develop`.
6. Releases: PR from `develop` to `main` with semver tag.

## Commit rules
- Format: `<type>: <short description>` (max 72 chars)
- Allowed types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `style`, `ci`
- Example: `feat: add tick-based memory decay engine`

## Sync with upstream Stanford
Monthly (or after relevant upstream releases):
```bash
git fetch upstream
git checkout develop
git merge upstream/main --no-ff -m "chore: sync with upstream Stanford joonspk-research/generative_agents"
```

## Branch protection (on GitHub)
- `main`: require PR, require status checks (ci/lint, ci/test), no force push, require review from code owners.
- `develop`: require PR, require status checks (ci/lint), no force push.
