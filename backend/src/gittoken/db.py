from datetime import UTC, datetime, timedelta

import httpx
from pydantic import BaseModel

from gittoken.domain import (
    Agent,
    AgenticCommit,
    GithubProfile,
    GithubUserId,
    VerifiedGithubUsername,
)

_TIMEOUT_SECONDS = 10
_USER_TTL = timedelta(days=1)


class _UserAgent(BaseModel):
    agent_id: Agent
    lines_added: int


class _User(BaseModel):
    github_id: int
    user_agents: list[_UserAgent]


async def fetch_cached_profile(
    supabase_url: str, secret_key: str, login: VerifiedGithubUsername
) -> GithubProfile | None:
    """Post: the profile saved in the last day, or None when there is none.
    Each agent's commits come back merged into one AgenticCommit."""
    fresh_since = datetime.now(UTC) - _USER_TTL
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
        response = await http_client.get(
            f"{supabase_url.rstrip('/')}/rest/v1/users",
            headers={"apikey": secret_key},
            params={
                "select": "github_id,user_agents(agent_id,lines_added)",
                "login": f"eq.{login.lower()}",
                "fetched_at": f"gte.{fresh_since.isoformat()}",
            },
        )
    response.raise_for_status()
    users = [_User.model_validate(row) for row in response.json()]
    if users:
        return GithubProfile(
            GithubUserId(users[0].github_id),
            login,
            tuple(
                AgenticCommit(user_agent.agent_id, user_agent.lines_added)
                for user_agent in users[0].user_agents
            ),
        )
    return None


async def save_profile(supabase_url: str, secret_key: str, profile: GithubProfile) -> None:
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
        response = await http_client.post(
            f"{supabase_url.rstrip('/')}/rest/v1/rpc/save_github_user",
            headers={"apikey": secret_key},
            json={
                "user_github_id": profile.github_id,
                "user_login": profile.login.lower(),
                "lines_added_by_agent": profile.lines_added_by_agent,
            },
        )
    response.raise_for_status()


class LeaderboardEntry(BaseModel):
    login: str
    total_tokens: int


async def fetch_leaderboard(supabase_url: str, secret_key: str) -> list[LeaderboardEntry]:
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
        response = await http_client.get(
            f"{supabase_url.rstrip('/')}/rest/v1/token_leaderboard",
            headers={"apikey": secret_key},
            params={
                "select": "login,total_tokens",
                "order": "total_tokens.desc,login.asc",
                "limit": "50",
            },
        )
    response.raise_for_status()
    return [LeaderboardEntry.model_validate(row) for row in response.json()]
