-- Rows without agents predate one-row profile saves; they are cache the API rebuilds on the next lookup.
delete from public.users where agents is null;

alter table public.users
  alter column agents set not null,
  add constraint users_agents_is_array check (jsonb_typeof(agents) = 'array');
