import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from itertools import batched
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
    PrivateRepository,
    ProfileStoreError,
    RepositoryId,
    VerifiedGithubUsername,
)

_TIMEOUT_SECONDS = 10
_USER_TTL = timedelta(days=1)
# A revoke event can list every repository of an installation; 50 keeps each URL near 4 KB.
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


class _GrantedRepository(BaseModel):
    repository_id: int = Field(gt=0)
    agents: list[_UserAgent]


class _User(BaseModel):
    github_id: int
    login: str = Field(pattern=GITHUB_LOGIN_PATTERN)
    agents: list[_UserAgent]
    granted_repositories: list[_GrantedRepository]


_USER_ROWS = TypeAdapter(list[_User])
_USER_COLUMNS = "github_id,login,agents,granted_repositories"


def _profile_from_user(user: _User, login: VerifiedGithubUsername) -> GithubProfile:
    return GithubProfile(
        GithubUserId(user.github_id),
        login,
        _lines_added_by_agent(user.agents),
        tuple(
            PrivateRepository(
                RepositoryId(private_repository.repository_id),
                _lines_added_by_agent(private_repository.agents),
            )
            for private_repository in user.granted_repositories
        ),
    )


async def fetch_cached_profile(
    supabase_client: SupabaseClient, login: VerifiedGithubUsername, now: datetime
) -> GithubProfile | None:
    """Post: the profile saved in the day before now with its public agents and private
    repositories, or None when there is none."""
    fresh_since = now - _USER_TTL
    request = supabase_client.build_request(
        "GET",
        "/users",
        params={
            "select": _USER_COLUMNS,
            "login": f"eq.{login.lower()}",
            "fetched_at": f"gte.{fresh_since.isoformat()}",
        },
    )
    users = _parse_rows(await _send(supabase_client, request), _USER_ROWS)
    if users:
        return _profile_from_user(users[0], login)
    return None


async def fetch_stored_profiles(
    supabase_client: SupabaseClient, github_ids: frozenset[GithubUserId]
) -> tuple[GithubProfile, ...]:
    """Post: the saved profile of each github_id that has a users row, whatever its age, with the
    login as stored."""
    joined_github_ids = ",".join(str(github_id) for github_id in github_ids)
    request = supabase_client.build_request(
        "GET",
        "/users",
        params={"select": _USER_COLUMNS, "github_id": f"in.({joined_github_ids})"},
    )
    users = _parse_rows(await _send(supabase_client, request), _USER_ROWS)
    return tuple(_profile_from_user(user, VerifiedGithubUsername(user.login)) for user in users)


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


def _granted_repository_rows(
    profile: GithubProfile,
) -> list[dict[str, int | list[dict[str, str | int]]]]:
    return [
        {
            "repository_id": private_repository.repository_id,
            "agents": _agent_rows(private_repository.lines_added_by_agent),
        }
        for private_repository in profile.private_repositories
    ]


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
            "agents": _agent_rows(profile.public_lines_added_by_agent),
            "granted_repositories": _granted_repository_rows(profile),
        },
    )
    await _send(supabase_client, request)


async def save_granted_repositories(
    supabase_client: SupabaseClient, profile: GithubProfile
) -> None:
    """Post: the account's users row holds the profile's private repositories and total, keeping
    its saved time."""
    request = supabase_client.build_request(
        "PATCH",
        "/users",
        params={"github_id": f"eq.{profile.github_id}"},
        json={
            "total_tokens": profile.total_tokens,
            "granted_repositories": _granted_repository_rows(profile),
        },
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


async def fetch_profiles_granting(
    supabase_client: SupabaseClient, repository_ids: tuple[RepositoryId, *tuple[RepositoryId, ...]]
) -> tuple[GithubProfile, ...]:
    """Post: the saved profile, whatever its age, of each account that granted any of
    repository_ids, once per account, with the login as stored."""
    profile_by_github_id: dict[GithubUserId, GithubProfile] = {}
    for repository_ids_batch in batched(repository_ids, _REPOSITORY_IDS_PER_REQUEST, strict=False):
        granted_filters = ",".join(
            f"granted_repositories.cs.{json.dumps([{'repository_id': repository_id}])}"
            for repository_id in repository_ids_batch
        )
        request = supabase_client.build_request(
            "GET", "/users", params={"select": _USER_COLUMNS, "or": f"({granted_filters})"}
        )
        for user in _parse_rows(await _send(supabase_client, request), _USER_ROWS):
            profile_by_github_id[GithubUserId(user.github_id)] = _profile_from_user(
                user, VerifiedGithubUsername(user.login)
            )
    return tuple(profile_by_github_id.values())


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
