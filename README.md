# GitToken

[GitFut](https://gitfut.com/) for token maxxers. Enter a GitHub username and get a shareable card showing the LLM tokens that developer spent through coding agents. The number is estimated from agent-attributed lines of code in their public repos.

Architecture proposal: [GitToken — Architecture Proposal](https://claude.ai/code/artifact/953dfeaf-4523-4951-aa18-eed07d207661)

## Architecture

```
Browser / README embed → CloudFront → S3 (React app)
                                    → api (FastAPI, ECS Fargate) → Supabase Postgres
                                                                 → SQS → worker (ECS Fargate) → GitHub API
```

- **api**: serves cached stats, SVG/PNG cards and the per-profile HTML shell with link-preview tags. Enqueues scouts.
- **worker**: crawls GitHub through the token broker, attributes commits to agents, runs the estimator.
- **Supabase**: Postgres (raw commits and derived stats), Realtime (scout progress), Auth (GitHub OAuth for opt-out).

## Layout

| Path | What | Owner |
| --- | --- | --- |
| `backend/src/gittoken/domain/` | Entities, attribution, LoC → tokens estimator. Pure Python | Lluc |
| `backend/src/gittoken/application/` | Use cases and ports | Lluc |
| `backend/src/gittoken/persistence/` | Supabase repositories | Mark |
| `backend/src/gittoken/integrations/` | GitHub client, token broker, SQS | Mark |
| `backend/src/gittoken/entrypoints/` | `api/`, `worker/`, `cli/` (calibrate) | Lluc |
| `backend/tests/` | `unit/`, `integration/` | Whoever owns the code under test |
| `frontend/` | React + Vite + TypeScript | Lluc |
| `infra/` | AWS CDK (Python): ECS, SQS, S3, CloudFront, alarms | Mark |
| `supabase/` | Migrations, RLS | Mark |
| `.github/` | CI/CD with GitHub Actions + AWS OIDC | Mark |

## Rules

Every directory has an `AGENTS.md` (≤ 10 lines) that humans and coding agents follow. `CLAUDE.md` imports it. The root one holds the global rules; [docs/CODING_RULES.md](docs/CODING_RULES.md) explains them in full.

## Plan

**Phase 0: spike (1 week).** Exit: we trust the estimates within 2×.
- [ ] Lluc: domain model, agent signatures, estimator v0, `calibrate` CLI on our own agent logs
- [ ] Mark: GitHub App, token broker, crawl 20 known profiles into local Supabase

**Phase 1: MVP (2–3 weeks).** Exit: any public username scouted in under 60 s.
- [ ] Lluc: use cases, `/v1` API, SVG card, profile and methodology pages
- [ ] Mark: schema and migrations, CDK stacks for dev, CI/CD, worker scaling on queue depth

**Phase 2: launch (2 weeks).** PNG and link-preview images, leaderboard, tiers, scheduled re-crawls, prod environment.

**Phase 3: Verified.** Opt-in upload of real usage from the `calibrate` CLI, estimator v2.
