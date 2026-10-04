# Backend: Python 3.13, uv, FastAPI. One package `gittoken`, three modules in src/gittoken/.
Imports point inward only: domain.py ← github.py ← api.py. Split a module into a folder, or add a layer, only when concrete code needs it.
- domain.py: agents, the agent email table, AgenticCommit, GithubProfile. Pure and sync: no I/O, no framework imports.
- The v0 formula and the email table are hardcoded constants in domain.py; versioning and loading them as data come later.
- github.py (owner: Marc): the only code that talks to GitHub. Parse every response with Pydantic into domain types. API only, never `git clone`. Explicit timeouts.
- api.py: the FastAPI composition root. Thin handlers, one pydantic-settings object, no os.environ elsewhere. Public routes live under /v1.
- Domain raises its own exception types; api.py maps them to HTTP status. No bare except.
- Full type annotations; `mypy --strict` clean. Must pass before commit: `uv run ruff format`, `uv run ruff check`, `uv run mypy src`.
