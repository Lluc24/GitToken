from collections.abc import Mapping
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
    PrivateRepository,
    ProfileStoreError,
    RepositoryId,
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


def _lines_added_by_agent(user_agents: list[_UserAgent]) -> MappingProxyType[Agent, int]:
    return MappingProxyType(
        {user_agent.agent_id: user_agent.lines_added for user_agent in user_agents}
    )


def _agent_rows(lines_added_by_agent: Mapping[Agent, int]) -> list[dict[str, str | int]]:
    return [
        {"agent_id": agent, "lines_added": lines_added}
        for agent, lines_added in lines_added_by_agent.items()
    ]


class _PrivateRepository(BaseModel):
    repository_id: int = Field(gt=0)
    agents: list[_UserAgent]


class _User(BaseModel):
    github_id: int
    agents: list[_UserAgent]
    private_repositories: list[_PrivateRepository]


_USER_ROWS = TypeAdapter(list[_User])


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
            "select": "github_id,agents,private_repositories(repository_id,agents)",
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
            _lines_added_by_agent(users[0].agents),
            tuple(
                PrivateRepository(
                    RepositoryId(private_repository.repository_id),
                    _lines_added_by_agent(private_repository.agents),
                )
                for private_repository in users[0].private_repositories
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
    """Post: the users row holds the public agents and the total with private repositories, and
    the account's private repository rows are exactly the profile's. The users row is written
    last, so a failed save leaves the cache stale and the next lookup rescans."""
    placeholder_request = supabase_client.build_request(
        "POST",
        "/users",
        headers={"Prefer": "resolution=ignore-duplicates"},
        params={"on_conflict": "github_id"},
        json={
            "github_id": profile.github_id,
            "login": profile.login.lower(),
            "fetched_at": now.isoformat(),
            "total_tokens": 0,
        },
    )
    await _send(supabase_client, placeholder_request)
    repository_ids = ",".join(
        str(private_repository.repository_id) for private_repository in profile.private_repositories
    )
    delete_request = supabase_client.build_request(
        "DELETE",
        "/private_repositories",
        params={"github_id": f"eq.{profile.github_id}"}
        | ({"repository_id": f"not.in.({repository_ids})"} if repository_ids else {}),
    )
    await _send(supabase_client, delete_request)
    if profile.private_repositories:
        upsert_request = supabase_client.build_request(
            "POST",
            "/private_repositories",
            headers={"Prefer": "resolution=merge-duplicates"},
            params={"on_conflict": "github_id,repository_id"},
            json=[
                {
                    "github_id": profile.github_id,
                    "repository_id": private_repository.repository_id,
                    "agents": _agent_rows(private_repository.lines_added_by_agent),
                    "scanned_at": now.isoformat(),
                }
                for private_repository in profile.private_repositories
            ],
        )
        await _send(supabase_client, upsert_request)
    user_request = supabase_client.build_request(
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
        },
    )
    await _send(supabase_client, user_request)


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
            "agents": "not.is.null",
            "order": "total_tokens.desc,login.asc",
            "limit": "50",
        },
    )
    rows = _parse_rows(await _send(supabase_client, request), _LEADERBOARD_ROWS)
    return tuple(
        LeaderboardEntry(VerifiedGithubUsername(row.login), row.total_tokens) for row in rows
    )
