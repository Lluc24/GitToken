# GitToken

![Python 3.13](https://img.shields.io/badge/python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Status: early prototype](https://img.shields.io/badge/status-early%20prototype-orange)

[GitFut](https://gitfut.com/) for token maxxers. Enter a GitHub username and get the LLM tokens that developer spent through coding agents, estimated from the agent commits in their public repos.

## How it works today

One FastAPI service with the public routes under /v1. Profiles are cached in Supabase for a day.

```mermaid
flowchart LR
    Browser -->|"GET /v1/users/{login}"| api[api.py]
    api -->|cache hit| db[db.py]
    db -->|REST| Supabase[(Supabase)]
    api -->|cache miss| github[github.py]
    github -->|GraphQL| GitHub[(GitHub API)]
    github -->|agentic commits| domain[domain.py]
    domain -->|tokens per agent| api
    api -->|save profile| db
```

1. Read the user's public, non-fork repos pushed to since 2025.
2. Keep the main-branch commits that have a coding agent among their authors or co-authors.
3. Tokens = lines added by those commits × 3,000 (a first guess).

The same data is drawn as SVG cards from Jinja templates, for the site and for READMEs. Add `?theme=light` for the light variant (dark by default); the badges page at `/badges` gives a README snippet that follows the reader's GitHub theme.

| Route | What |
| --- | --- |
| `GET /v1/users/{login}` | Total and per-agent tokens, rarity |
| `GET /v1/badges/{login}/profile.svg` | Profile card with the GitHub avatar inlined |
| `GET /v1/badges/{login}.svg` | Card without the photo |
| `GET /v1/leaderboard` | Profiles scanned in the last day |

Profiles and cards are cached by the CDN for a day, matching the Supabase cache. GitHub's image proxy gives up after a few seconds, so a card whose first scan takes longer answers with a "Scanning" placeholder for a minute while the scan finishes.

```
make setup     # install everything, enable the pre-commit hook
FASTAPI_ENV=development GITHUB_TOKEN=$(gh auth token) uv run uvicorn gittoken.api:app   # API on :8000
make dev-web   # page on http://localhost:5173, proxies /v1 to the API
make check     # format, lint, typecheck: the same gate CI runs
make fix       # auto-format and auto-fix
```

Needs uv, pnpm and make.

Deployed on Vercel as one project: the FastAPI app also serves the built page. `vercel deploy --prod` from the repo root; the Vercel settings are under `[tool.vercel]` in `pyproject.toml`.

## Layout

| Path | What | Owner |
| --- | --- | --- |
| `backend/src/gittoken/domain.py` | Agents, agent emails, the lines → tokens formula | Lluc |
| `backend/src/gittoken/github.py` | GitHub GraphQL queries | Marc |
| `backend/src/gittoken/db.py` | Supabase profile cache | Lluc |
| `backend/src/gittoken/api.py` | FastAPI app and the `/v1` routes | Lluc |
| `backend/src/gittoken/badge.py`, `templates/` | SVG cards: Jinja templates, palette, agent logos | Lluc |
| `frontend/` | React site: search, profile card, badges, leaderboard | Lluc |
| `infra/`, `supabase/`, `.github/` | AWS (not started), database and CI/CD | Marc |

## Rules

We start in the simplest shape that works and add structure when concrete code needs it. `AGENTS.md` (≤ 10 lines per directory) holds the rules humans and coding agents follow; `CLAUDE.md` imports it. [CONTRIBUTING.md](CONTRIBUTING.md) holds the PR workflow; [docs/CODING_RULES.md](docs/CODING_RULES.md) explains the coding rules in full.

## Next, each when it is needed

- **Better estimate**: calibrate the formula on real agent logs; show a range.
- **Scale**: several GitHub tokens, then a queue and workers if a profile is too slow to compute in one request.
- **Launch**: link previews showing the card, then deployment.

The long-term design is in the [architecture proposal](https://claude.ai/code/artifact/953dfeaf-4523-4951-aa18-eed07d207661).
