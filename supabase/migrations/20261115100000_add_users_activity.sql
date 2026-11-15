-- Agent commits and lines added per UTC day, public repositories only. Saved rows start empty
-- until their next scan.
alter table public.users
  add column activity jsonb not null default '[]',
  add constraint users_activity_is_array check (jsonb_typeof(activity) = 'array');
