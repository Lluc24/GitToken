-- Agent commits and lines added per UTC day, public repositories only; each granted repository
-- carries its own so withdrawing it forgets them. Saved rows start empty until their next scan.
alter table public.users
  add column activity jsonb not null default '[]',
  add constraint users_activity_is_array check (jsonb_typeof(activity) = 'array');

update public.users
set granted_repositories = (
  select coalesce(jsonb_agg(repository || '{"activity": []}'), '[]')
  from jsonb_array_elements(granted_repositories) as repository
);
