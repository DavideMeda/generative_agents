# Branch Strategy — Gen_Agent (fork-first)

## Branch permanenti

| Branch    | Scopo                                         | Protezione |
|-----------|-----------------------------------------------|------------|
| `main`    | Codice stabile, pronto per produzione         | Sì — require PR + CI verde |
| `develop` | Integrazione continua feature/fix             | Sì — require PR + CI verde |

## Branch temporanei (naming convention)

```
feature/<descrizione-breve>   # nuova funzionalità
refactor/<modulo>             # refactoring interno
fix/<descrizione-bug>         # bugfix
docs/<argomento>              # solo documentazione
chore/<task>                  # manutenzione, deps, config
```

## Workflow standard

1. Crea branch da `develop`: `git checkout -b feature/mia-feature develop`
2. Sviluppa + testa localmente.
3. Apri PR verso `develop` — CI deve essere verde.
4. Code review obbligatoria (almeno 1 reviewer).
5. Squash merge in `develop`.
6. Ogni release: PR da `develop` a `main` con tag semver.

## Regole commit

Formato: `<tipo>: <breve descrizione>` (massimo 72 caratteri)

Tipi ammessi: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `style`, `ci`

Esempio: `feat: add tick-based memory decay engine`

## Sincronizzazione con upstream Stanford

Mensilmente (o a ogni release Stanford rilevante):

```bash
git fetch upstream
git checkout develop
git merge upstream/main --no-ff -m "chore: sync with upstream Stanford joonspk-research/generative_agents"
```

## Branch protection rules (da applicare su GitHub)

- `main`: require PR, require status checks (ci/lint, ci/test), no force push, require review from code owners.
- `develop`: require PR, require status checks (ci/lint), no force push.
