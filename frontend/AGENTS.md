# Frontend (owner: Lluc): React, Vite, TypeScript strict, pnpm, TanStack Query, Tailwind.
Layers in src/: domain ← application ← infrastructure, ui. Root AGENTS.md rules apply to TypeScript too.
- domain/: pure types and functions (token formatting, tiers). No React, no fetch.
- infrastructure/: API client generated from the backend OpenAPI, Supabase Realtime. The only place that does I/O.
- application/: TanStack Query hooks over infrastructure. Components never call fetch.
- ui/: components and pages. Typed props; no `any`, no non-null `!`, no `as` casts. Accessible markup.
- Biome owns lint and format; `make check` (biome ci, tsc) passes before commit.
