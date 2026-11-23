.PHONY: setup check check-backend check-frontend fix dev-web repo-bootstrap

setup:
	uv sync --all-packages
	cd frontend && pnpm install
	git config core.hooksPath .githooks

check: check-backend check-frontend

check-backend:
	uv run ruff format --check
	uv run ruff check
	uv run mypy backend/src

check-frontend:
	cd frontend && pnpm check
	cd frontend && pnpm build

fix:
	uv run ruff format
	uv run ruff check --fix
	cd frontend && pnpm fix

dev-web:
	cd frontend && pnpm dev

# One-time, by a repo admin with gh authenticated: squash-only merges, auto-delete branches, main ruleset.
repo-bootstrap:
	gh api -X PATCH repos/Lluc24/gittoken -f default_branch=main -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false -F delete_branch_on_merge=true -F allow_auto_merge=true -F allow_update_branch=true -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY
	gh api -X POST repos/Lluc24/gittoken/rulesets --input .github/rulesets/main.json
	git push origin --delete master
