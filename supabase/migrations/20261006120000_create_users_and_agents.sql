create table public.users (
  github_id bigint primary key,
  login text not null unique check (login = lower(login)),
  fetched_at timestamptz not null
);

create table public.agents (
  id text primary key
);

insert into public.agents (id) values
  ('claude_code'), ('codex'), ('copilot'), ('cursor'), ('devin'), ('jules'), ('aider');

create table public.user_agents (
  github_id bigint not null references public.users (github_id) on delete cascade,
  agent_id text not null references public.agents (id),
  lines_added bigint not null check (lines_added >= 0),
  primary key (github_id, agent_id)
);

alter table public.users enable row level security;
alter table public.agents enable row level security;
alter table public.user_agents enable row level security;

-- One call so a refresh replaces a user's rows atomically. A login now owned by another
-- GitHub id belongs to a renamed account, so that stale user is dropped.
create function public.save_github_user(
  user_github_id bigint, user_login text, lines_added_by_agent jsonb
) returns void
language sql
set search_path = ''
as $$
  delete from public.users where login = user_login and github_id <> user_github_id;
  insert into public.users (github_id, login, fetched_at)
    values (user_github_id, user_login, now())
    on conflict (github_id) do update set login = excluded.login, fetched_at = excluded.fetched_at;
  delete from public.user_agents where github_id = user_github_id;
  insert into public.user_agents (github_id, agent_id, lines_added)
    select user_github_id, agent.key, agent.value::bigint
    from jsonb_each_text(lines_added_by_agent) as agent;
$$;

revoke execute on function public.save_github_user from public, anon, authenticated;
