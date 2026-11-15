create index users_granted_repository_ids_idx on public.users using gin (granted_repository_ids);
