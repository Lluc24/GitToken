-- Rows saved before one-row profiles are stale; the next lookup rescans them and rewrites agents.
update public.users set agents = '[]'::jsonb where agents is null;

alter table public.users
  alter column agents set not null,
  add constraint users_agents_is_array check (jsonb_typeof(agents) = 'array');
