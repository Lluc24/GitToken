from collections import Counter

from pydantic import BaseModel
from redis.asyncio import Redis

from gittoken.domain import (
    Agent,
    AgenticCommit,
    GithubProfile,
    GithubUserId,
    VerifiedGithubUsername,
)

_PROFILE_TTL_SECONDS = 86400


class _CachedProfile(BaseModel):
    github_id: int
    login: str
    lines_added_by_agent: dict[Agent, int]


def _key(login: str) -> str:
    return f"gittoken:profile:v1:{login.lower()}"


async def fetch_profile_cache(
    redis_url: str, login: VerifiedGithubUsername
) -> GithubProfile | None:
    async with Redis.from_url(
        redis_url, decode_responses=True, socket_timeout=5, socket_connect_timeout=5
    ) as client:
        payload = await client.get(_key(login))
    if payload is not None:
        saved = _CachedProfile.model_validate_json(payload)
        return GithubProfile(
            GithubUserId(saved.github_id),
            VerifiedGithubUsername(saved.login),
            tuple(
                AgenticCommit(agent, lines) for agent, lines in saved.lines_added_by_agent.items()
            ),
        )
    return None


async def save_profile_cache(redis_url: str, profile: GithubProfile) -> None:
    lines: Counter[Agent] = Counter()
    for commit in profile.agentic_commits:
        lines[commit.agent] += commit.lines_added
    saved = _CachedProfile(
        github_id=profile.github_id,
        login=profile.login,
        lines_added_by_agent=dict(lines),
    )
    async with Redis.from_url(
        redis_url, decode_responses=True, socket_timeout=5, socket_connect_timeout=5
    ) as client:
        await client.set(_key(profile.login), saved.model_dump_json(), ex=_PROFILE_TTL_SECONDS)
