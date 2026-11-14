create index users_granted_repositories_idx on public.users using gin (granted_repositories jsonb_path_ops);
