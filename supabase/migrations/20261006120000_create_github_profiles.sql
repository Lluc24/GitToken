create table public.github_profiles (
  login text primary key check (login = lower(login)),
  lines_added_by_agent jsonb not null check (jsonb_typeof(lines_added_by_agent) = 'object'),
  fetched_at timestamptz not null default now()
);

alter table public.github_profiles enable row level security;
