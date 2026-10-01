# Persistence (owner: Marc): Supabase Postgres repositories implementing application ports.
- A database read is a boundary: parse rows into domain types here. Domain types never know about rows.
- SQL lives only in this layer. Parametrized queries, never string formatting.
- Schema changes only through supabase/migrations. Raw GitHub facts and derived stats stay in separate tables.
