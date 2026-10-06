from collections import Counter
from datetime import UTC, datetime, timedelta

import httpx
from pydantic import BaseModel

from gittoken.domain import Agent, AgenticCommit, GithubProfile, VerifiedGithubUsername

_TIMEOUT_SECONDS = 10
_PROFILE_TTL = timedelta(days=1)


class _CachedProfile(BaseModel):
    lines_added_by_agent: dict[Agent, int]


def _profiles_url(supabase_url: str) -> str:
    return f"{supabase_url.rstrip('/')}/rest/v1/github_profiles"


async def fetch_cached_profile(
    supabase_url: str, secret_key: str, login: VerifiedGithubUsername
) -> GithubProfile | None:
    """Post: the profile cached in the last day, or None when there is none.
    Each agent's commits come back merged into one AgenticCommit."""
    fresh_since = datetime.now(UTC) - _PROFILE_TTL
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
        response = await http_client.get(
            _profiles_url(supabase_url),
            headers={"apikey": secret_key},
            params={
                "select": "lines_added_by_agent",
                "login": f"eq.{login.lower()}",
                "fetched_at": f"gte.{fresh_since.isoformat()}",
            },
        )
    response.raise_for_status()
    rows = [_CachedProfile.model_validate(row) for row in response.json()]
    if not rows:
        return None
    return GithubProfile(
        login,
        tuple(
            AgenticCommit(agent, lines_added)
            for agent, lines_added in rows[0].lines_added_by_agent.items()
        ),
    )


async def save_profile(supabase_url: str, secret_key: str, profile: GithubProfile) -> None:
    lines_added_by_agent: Counter[Agent] = Counter()
    for agentic_commit in profile.agentic_commits:
        lines_added_by_agent[agentic_commit.agent] += agentic_commit.lines_added
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
        response = await http_client.post(
            _profiles_url(supabase_url),
            headers={"apikey": secret_key, "Prefer": "resolution=merge-duplicates"},
            json={
                "login": profile.login.lower(),
                "lines_added_by_agent": lines_added_by_agent,
                "fetched_at": datetime.now(UTC).isoformat(),
            },
        )
    response.raise_for_status()
