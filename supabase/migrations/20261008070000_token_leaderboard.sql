create view public.token_leaderboard with (security_invoker = true) as
select users.login, coalesce(sum(user_agents.lines_added), 0)::bigint * 3000 as total_tokens
from public.users
left join public.user_agents using (github_id)
where users.fetched_at >= now() - interval '1 day'
group by users.github_id, users.login;

revoke all on public.token_leaderboard from public, anon, authenticated;
grant select on public.token_leaderboard to service_role;
