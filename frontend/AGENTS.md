# Frontend (owner: Lluc): React, Vite, TypeScript strict, pnpm, TanStack Query, Tailwind. Not started.
Start flat in src/. Split into folders, or add a layer, only when concrete code needs it. Root AGENTS.md rules apply to TypeScript too.
- Pure types and functions (token formatting) stay free of React and fetch.
- One module does the I/O: the client for the backend /v1 routes. Components never call fetch; they use TanStack Query hooks over it.
- Components have typed props; no `any`, no non-null `!`, no `as` casts. Accessible markup.
- Biome owns lint and format. `pnpm check` passes before commit.
