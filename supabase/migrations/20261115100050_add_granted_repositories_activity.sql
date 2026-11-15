-- Each granted repository carries its own activity so withdrawing it forgets them; saved
-- repositories start empty until their next scan.
update public.users
set granted_repositories = (
  select coalesce(jsonb_agg(repository || '{"activity": []}'), '[]')
  from jsonb_array_elements(granted_repositories) as repository
);
