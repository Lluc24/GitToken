# Backend: Python 3.13, uv, FastAPI. One package `gittoken`, four modules in src/gittoken/.
Imports point inward only: domain.py ← github.py, db.py ← api.py. Split a module into a folder, or add a layer, only when concrete code needs it.
- domain.py: agents, the agent email table, AgenticCommit, GithubProfile. Pure and sync: no I/O, no framework imports.
- The v0 formula and the email table are hardcoded constants in domain.py; versioning and loading them as data come later.
- github.py (owner: Marc): the only code that talks to GitHub. Parse every response with Pydantic into domain types. API only, never `git clone`. Explicit timeouts.
- db.py: the only code that talks to Supabase, through its REST API. Caches each profile for a day. A new Agent needs a migration adding it to the agents table.
- api.py: the FastAPI composition root. Thin handlers, one pydantic-settings object, no os.environ elsewhere. Public routes live under /v1.
- Domain raises its own exception types; api.py maps them to HTTP status. No bare except.
- Full type annotations; `mypy --strict` clean. `make check` passes before commit; ruff and mypy config live in the root pyproject.toml.
