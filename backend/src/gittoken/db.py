from datetime import datetime, timedelta
from types import MappingProxyType
from typing import NewType

import httpx
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    NonNegativeInt,
    SecretStr,
    TypeAdapter,
    ValidationError,
)

from gittoken.domain import (
    GITHUB_LOGIN_PATTERN,
    Agent,
    GithubProfile,
    GithubUserId,
    LeaderboardEntry,
    ProfileStoreError,
    VerifiedGithubUsername,
)

_TIMEOUT_SECONDS = 10
_USER_TTL = timedelta(days=1)

SupabaseClient = NewType("SupabaseClient", httpx.AsyncClient)


def create_supabase_client(supabase_url: HttpUrl, secret_key: SecretStr) -> SupabaseClient:
    return SupabaseClient(
        httpx.AsyncClient(
            base_url=f"{str(supabase_url).rstrip('/')}/rest/v1",
            headers={"apikey": secret_key.get_secret_value()},
            timeout=_TIMEOUT_SECONDS,
        )
    )


async def _send(supabase_client: SupabaseClient, request: httpx.Request) -> httpx.Response:
    try:
        response = await supabase_client.send(request)
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise ProfileStoreError(
            f"Supabase could not complete {request.method} {request.url.path}"
        ) from error
    return response


def _parse_rows[Row](response: httpx.Response, rows_adapter: TypeAdapter[list[Row]]) -> list[Row]:
    try:
        return rows_adapter.validate_json(response.content)
    except ValidationError as error:
        raise ProfileStoreError("Supabase returned rows of an unexpected shape") from error


class _UserAgent(BaseModel):
    agent_id: Agent
    lines_added: NonNegativeInt


class _User(BaseModel):
    github_id: int
    agents: list[_UserAgent]


_USER_ROWS = TypeAdapter(list[_User])


async def fetch_cached_profile(
    supabase_client: SupabaseClient, login: VerifiedGithubUsername, now: datetime
) -> GithubProfile | None:
    """Post: the profile saved in the day before now with its agents, or None when there is none."""
    fresh_since = now - _USER_TTL
    request = supabase_client.build_request(
        "GET",
        "/users",
        params={
            "select": "github_id,agents",
            "login": f"eq.{login.lower()}",
            "fetched_at": f"gte.{fresh_since.isoformat()}",
            "agents": "not.is.null",
        },
    )
    users = _parse_rows(await _send(supabase_client, request), _USER_ROWS)
    if users:
        return GithubProfile(
            GithubUserId(users[0].github_id),
            login,
            MappingProxyType(
                {user_agent.agent_id: user_agent.lines_added for user_agent in users[0].agents}
            ),
        )
    return None


async def delete_renamed_user(supabase_client: SupabaseClient, profile: GithubProfile) -> None:
    """Post: no other GitHub id holds this profile's login, which a renamed account may have left."""
    request = supabase_client.build_request(
        "DELETE",
        "/users",
        params={
            "login": f"eq.{profile.login.lower()}",
            "github_id": f"neq.{profile.github_id}",
        },
    )
    await _send(supabase_client, request)


async def save_profile(
    supabase_client: SupabaseClient, profile: GithubProfile, now: datetime
) -> None:
    request = supabase_client.build_request(
        "POST",
        "/users",
        headers={"Prefer": "resolution=merge-duplicates"},
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
    await _send(supabase_client, request)


class _LeaderboardRow(BaseModel):
    login: str = Field(pattern=GITHUB_LOGIN_PATTERN)
    total_tokens: NonNegativeInt


_LEADERBOARD_ROWS = TypeAdapter(list[_LeaderboardRow])


async def fetch_leaderboard(
    supabase_client: SupabaseClient, now: datetime
) -> tuple[LeaderboardEntry, ...]:
    fresh_since = now - _USER_TTL
    request = supabase_client.build_request(
        "GET",
        "/users",
        params={
            "select": "login,total_tokens",
            "fetched_at": f"gte.{fresh_since.isoformat()}",
            "order": "total_tokens.desc,login.asc",
            "limit": "50",
        },
    )
    rows = _parse_rows(await _send(supabase_client, request), _LEADERBOARD_ROWS)
    return tuple(
        LeaderboardEntry(VerifiedGithubUsername(row.login), row.total_tokens) for row in rows
    )
