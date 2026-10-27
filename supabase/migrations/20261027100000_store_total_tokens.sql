alter table public.users add column total_tokens bigint check (total_tokens >= 0);

update public.users
set total_tokens = coalesce(
  (select sum(lines_added) from public.user_agents where user_agents.github_id = users.github_id), 0
) * 3000;

alter table public.users alter column total_tokens set not null;

drop view public.token_leaderboard;

drop function public.save_github_user(bigint, text, jsonb);

create function public.save_github_user(
  user_github_id bigint, user_login text, user_total_tokens bigint, lines_added_by_agent jsonb
) returns void
language sql
set search_path = ''
as $$
  delete from public.users where login = user_login and github_id <> user_github_id;
  insert into public.users (github_id, login, fetched_at, total_tokens)
    values (user_github_id, user_login, now(), user_total_tokens)
    on conflict (github_id) do update
      set login = excluded.login, fetched_at = excluded.fetched_at, total_tokens = excluded.total_tokens;
  delete from public.user_agents where github_id = user_github_id;
  insert into public.user_agents (github_id, agent_id, lines_added)
    select user_github_id, agent.key, agent.value::bigint
    from jsonb_each_text(lines_added_by_agent) as agent;
$$;

revoke execute on function public.save_github_user from public, anon, authenticated;
