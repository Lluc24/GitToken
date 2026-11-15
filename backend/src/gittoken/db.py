from collections.abc import Mapping
from datetime import date, datetime, timedelta
from itertools import batched
from types import MappingProxyType
from typing import NewType

import httpx
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    NonNegativeInt,
    PositiveInt,
    SecretStr,
    TypeAdapter,
    ValidationError,
)

from gittoken.domain import (
    GITHUB_LOGIN_PATTERN,
    Agent,
    DayActivity,
    GithubProfile,
    GithubUserId,
    LeaderboardEntry,
    ProfileStoreError,
    RepositoryId,
    VerifiedGithubUsername,
)

_TIMEOUT_SECONDS = 10
_USER_TTL = timedelta(days=1)
# A revoke event can list every repository of an installation; 50 ids keep each URL under 1 KB.
_REPOSITORY_IDS_PER_REQUEST = 50

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


def _lines_added_by_agent(user_agents: list[_UserAgent]) -> MappingProxyType[Agent, int]:
    return MappingProxyType(
        {user_agent.agent_id: user_agent.lines_added for user_agent in user_agents}
    )


def _agent_rows(lines_added_by_agent: Mapping[Agent, int]) -> list[dict[str, str | int]]:
    return [
        {"agent_id": agent, "lines_added": lines_added}
        for agent, lines_added in lines_added_by_agent.items()
    ]


class _DayActivity(BaseModel):
    day: date
    commits: PositiveInt
    lines_added: NonNegativeInt


def _activity_by_day(
    day_activities: list[_DayActivity],
) -> MappingProxyType[date, DayActivity]:
    return MappingProxyType(
        {
            day_activity.day: DayActivity(day_activity.commits, day_activity.lines_added)
            for day_activity in day_activities
        }
    )


def _activity_rows(activity_by_day: Mapping[date, DayActivity]) -> list[dict[str, str | int]]:
    return [
        {"day": day.isoformat(), "commits": activity.commits, "lines_added": activity.lines_added}
        for day, activity in activity_by_day.items()
    ]


class _User(BaseModel):
    github_id: int
    agents: list[_UserAgent]
    activity: list[_DayActivity]
    granted_repository_ids: list[PositiveInt]


_USER_ROWS = TypeAdapter(list[_User])


def _profile_from_user(user: _User, login: VerifiedGithubUsername) -> GithubProfile:
    return GithubProfile(
        GithubUserId(user.github_id),
        login,
        _lines_added_by_agent(user.agents),
        _activity_by_day(user.activity),
        tuple(RepositoryId(repository_id) for repository_id in user.granted_repository_ids),
    )


async def fetch_cached_profile(
    supabase_client: SupabaseClient, login: VerifiedGithubUsername, now: datetime
) -> GithubProfile | None:
    """Post: the profile saved in the day before now, or None when there is none."""
    fresh_since = now - _USER_TTL
    request = supabase_client.build_request(
        "GET",
        "/users",
        params={
            "select": "github_id,agents,activity,granted_repository_ids",
            "login": f"eq.{login.lower()}",
            "fetched_at": f"gte.{fresh_since.isoformat()}",
        },
    )
    users = _parse_rows(await _send(supabase_client, request), _USER_ROWS)
    if users:
        return _profile_from_user(users[0], login)
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
    """Post: the account's users row holds the profile, saved at now, in one atomic upsert."""
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
            "agents": _agent_rows(profile.lines_added_by_agent),
            "activity": _activity_rows(profile.activity_by_day),
            "granted_repository_ids": list(profile.private_repository_ids),
        },
    )
    await _send(supabase_client, request)


async def delete_profile(supabase_client: SupabaseClient, github_id: GithubUserId) -> None:
    """Post: the account has no saved profile, so the next lookup rescans it."""
    request = supabase_client.build_request(
        "DELETE", "/users", params={"github_id": f"eq.{github_id}"}
    )
    await _send(supabase_client, request)


async def delete_profile_saved_before(
    supabase_client: SupabaseClient, github_id: GithubUserId, saved_before: datetime
) -> None:
    """Post: if the account's profile was saved before saved_before, it is gone, so the next
    lookup rescans it."""
    request = supabase_client.build_request(
        "DELETE",
        "/users",
        params={"github_id": f"eq.{github_id}", "fetched_at": f"lt.{saved_before.isoformat()}"},
    )
    await _send(supabase_client, request)


async def delete_profiles_granting(
    supabase_client: SupabaseClient, repository_ids: tuple[RepositoryId, *tuple[RepositoryId, ...]]
) -> None:
    """Post: no saved profile covers any of repository_ids, so each such account's next lookup
    rescans it."""
    for repository_ids_batch in batched(repository_ids, _REPOSITORY_IDS_PER_REQUEST, strict=False):
        joined_repository_ids = ",".join(
            str(repository_id) for repository_id in repository_ids_batch
        )
        request = supabase_client.build_request(
            "DELETE",
            "/users",
            params={"granted_repository_ids": f"ov.{{{joined_repository_ids}}}"},
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
