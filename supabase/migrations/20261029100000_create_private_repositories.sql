-- Holds only an opaque repository id and per-agent line counts: no names, messages or code.
create table public.private_repositories (
  github_id bigint not null references public.users (github_id) on delete cascade,
  repository_id bigint not null check (repository_id > 0),
  agents jsonb not null check (jsonb_typeof(agents) = 'array'),
  scanned_at timestamptz not null,
  primary key (github_id, repository_id)
);

alter table public.private_repositories enable row level security;
