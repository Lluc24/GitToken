-- Holds only opaque repository ids and per-agent line counts: no names, messages or code.
alter table public.users
  add column granted_repositories jsonb not null default '[]',
  add constraint users_granted_repositories_is_array check (jsonb_typeof(granted_repositories) = 'array');
