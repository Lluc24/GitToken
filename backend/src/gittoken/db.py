from datetime import datetime, timedelta
from types import MappingProxyType

import httpx
from pydantic import BaseModel, NonNegativeInt

from gittoken.domain import (
    Agent,
    GithubProfile,
    GithubUserId,
    VerifiedGithubUsername,
)

_TIMEOUT_SECONDS = 10
_USER_TTL = timedelta(days=1)


class _UserAgent(BaseModel):
    agent_id: Agent
    lines_added: NonNegativeInt


class _User(BaseModel):
    github_id: int
    agents: list[_UserAgent]


async def fetch_cached_profile(
    supabase_url: str, secret_key: str, login: VerifiedGithubUsername, now: datetime
) -> GithubProfile | None:
    """Post: the profile saved in the day before now with its agents, or None when there is none."""
    fresh_since = now - _USER_TTL
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
        response = await http_client.get(
            f"{supabase_url.rstrip('/')}/rest/v1/users",
            headers={"apikey": secret_key},
            params={
                "select": "github_id,agents",
                "login": f"eq.{login.lower()}",
                "fetched_at": f"gte.{fresh_since.isoformat()}",
                "agents": "not.is.null",
            },
        )
    response.raise_for_status()
    users = [_User.model_validate(row) for row in response.json()]
    if users:
        return GithubProfile(
            GithubUserId(users[0].github_id),
            login,
            MappingProxyType(
                {user_agent.agent_id: user_agent.lines_added for user_agent in users[0].agents}
            ),
        )
    return None


async def delete_renamed_user(supabase_url: str, secret_key: str, profile: GithubProfile) -> None:
    """Post: no other GitHub id holds this profile's login, which a renamed account may have left."""
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
        response = await http_client.delete(
            f"{supabase_url.rstrip('/')}/rest/v1/users",
            headers={"apikey": secret_key},
            params={
                "login": f"eq.{profile.login.lower()}",
                "github_id": f"neq.{profile.github_id}",
            },
        )
    response.raise_for_status()


async def save_profile(
    supabase_url: str, secret_key: str, profile: GithubProfile, now: datetime
) -> None:
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
        response = await http_client.post(
            f"{supabase_url.rstrip('/')}/rest/v1/users",
            headers={"apikey": secret_key, "Prefer": "resolution=merge-duplicates"},
            params={"on_conflict": "github_id"},
            json={
                "github_id": profile.github_id,
                "login": profile.login.lower(),
                "fetched_at": now.isoformat(),
                "total_tokens": profile.total_tokens,
                "agents": [
                    {"agent_id": agent, "lines_added": lines_added}
                    for agent, lines_added in profile.lines_added_by_agent.items()
                ],
            },
        )
    response.raise_for_status()


class LeaderboardEntry(BaseModel):
    login: str
    total_tokens: int


async def fetch_leaderboard(
    supabase_url: str, secret_key: str, now: datetime
) -> list[LeaderboardEntry]:
    fresh_since = now - _USER_TTL
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
        response = await http_client.get(
            f"{supabase_url.rstrip('/')}/rest/v1/users",
            headers={"apikey": secret_key},
            params={
                "select": "login,total_tokens",
                "fetched_at": f"gte.{fresh_since.isoformat()}",
                "order": "total_tokens.desc,login.asc",
                "limit": "50",
            },
        )
    response.raise_for_status()
    return [LeaderboardEntry.model_validate(row) for row in response.json()]
