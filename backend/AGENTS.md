# Backend: Python 3.13, uv, FastAPI. One package `gittoken`, one Docker image, run as the api and worker ECS services.
Layers in src/gittoken/: domain ← application ← persistence, integrations, entrypoints. Never import outward.
- Full type annotations; `mypy --strict` clean. Domain uses frozen dataclasses and enums; Pydantic only at boundaries.
- Must pass before commit: `uv run ruff format`, `uv run ruff check`, `uv run mypy src`, `uv run pytest`.
- Domain and application raise their own exception types; entrypoints map them to HTTP status or exit codes. No bare except.
- Config: one pydantic-settings object built in the entrypoint and passed down. No os.environ anywhere else.
- No globals or singletons. Dependencies are wired in entrypoints (composition root) and injected.
- Domain is pure and sync. Application, persistence and integrations are async.
