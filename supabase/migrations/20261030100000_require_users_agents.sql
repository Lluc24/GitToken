-- Every row is at most a day of cache, recomputed from GitHub on the next lookup.
delete from public.users;

alter table public.users
  alter column agents set not null,
  add constraint users_agents_is_array check (jsonb_typeof(agents) = 'array');
