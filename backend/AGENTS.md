# Backend: Python 3.13, uv, FastAPI. One package `gittoken` in src/gittoken/.
Imports point inward only: domain.py ← github.py, db.py ← application.py ← api.py. Split a module into a folder, or add a layer, only when concrete code needs it.
- domain.py: agents, the agent email table, the GitHub login format, the token and rarity rules, GithubProfile, LeaderboardEntry. Pure and sync: no I/O, no framework imports.
- The v0 formula and the email table are hardcoded constants in domain.py; versioning and loading them as data come later.
- github.py (owner: Marc): the only code that talks to GitHub. Parse every response with Pydantic into domain types. API only, never `git clone`. Explicit timeouts.
- db.py: the only code that talks to Supabase, through its REST API. Only maps rows to domain types and back; takes `now`, never reads the clock. Caches each profile for a day.
- application.py: orchestrates each use case (cache read, scan, save) and reads the clock once, passing `now` to db.py.
- api.py: the FastAPI composition root, HTTP concerns only: routes, status mapping, cache headers, badge dedupe. Thin handlers, one pydantic-settings object, no os.environ elsewhere. Public routes live under /v1.
- Each adapter owns one shared HTTP client per service and turns transport and parse failures into domain exceptions; api.py creates the clients and maps the exceptions to HTTP status. No bare except.
- Full type annotations; `mypy --strict` clean. No `Any`, no `cast`, no bare `type: ignore`: ruff and mypy reject them. `make check` passes before commit; ruff and mypy config live in the root pyproject.toml.
