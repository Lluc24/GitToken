.PHONY: setup check fix dev-web

setup:
	uv sync --all-packages
	pnpm --dir frontend install
	git config core.hooksPath .githooks

check:
	uv run ruff format --check
	uv run ruff check
	uv run mypy backend/src
	uv run mypy infra
	pnpm --dir frontend check

fix:
	uv run ruff format
	uv run ruff check --fix
	pnpm --dir frontend fix

dev-web:
	pnpm --dir frontend dev
