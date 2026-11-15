-- Agent commits and lines added per UTC authored day, public and private repositories combined.
alter table public.users
  add column activity jsonb not null,
  add constraint users_activity_is_array check (jsonb_typeof(activity) = 'array');
