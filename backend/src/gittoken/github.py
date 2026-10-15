import asyncio
from itertools import chain
from json import JSONDecodeError
from typing import Self

import httpx
from pydantic import BaseModel, Field, ValidationError, model_validator

from gittoken.domain import (
    AgenticCommit,
    GithubProfile,
    GithubRequestError,
    GithubUserId,
    ProfileNotFoundError,
    VerifiedGithubUsername,
    find_agent,
)

_GRAPHQL_URL = "https://api.github.com/graphql"
_TIMEOUT_SECONDS = 30
_MAXIMUM_CONNECTIONS = 8
# GitHub timestamps are UTC ISO 8601, so they compare correctly as strings.
_COMMITS_SINCE = "2025-01-01T00:00:00Z"

_REPOSITORIES_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    databaseId
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC,
                 orderBy: {field: PUSHED_AT, direction: DESC}, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes { id pushedAt }
    }
  }
}
"""

_COMMITS_QUERY = """
query($repositoryId: ID!, $since: GitTimestamp!, $cursor: String) {
  node(id: $repositoryId) {
    ... on Repository {
      defaultBranchRef {
        target {
          ... on Commit {
            history(first: 100, since: $since, after: $cursor) {
              pageInfo { hasNextPage endCursor }
              nodes { additions authors(first: 100) { pageInfo { hasNextPage endCursor } nodes { email } } }
            }
          }
        }
      }
    }
  }
}
"""


class _Repository(BaseModel):
    id: str
    pushed_at: str | None = Field(alias="pushedAt")


class _PageInfo(BaseModel):
    has_next_page: bool = Field(alias="hasNextPage")
    end_cursor: str | None = Field(alias="endCursor")

    @model_validator(mode="after")
    def validate_cursor(self) -> Self:
        if self.has_next_page and not self.end_cursor:
            raise ValueError("a next page requires a non-empty cursor")
        return self


class _Repositories(BaseModel):
    page_info: _PageInfo = Field(alias="pageInfo")
    nodes: list[_Repository]


class _User(BaseModel):
    database_id: int = Field(alias="databaseId")
    repositories: _Repositories


class _UserData(BaseModel):
    user: _User | None


class _GraphqlError(BaseModel):
    message: str


class _GraphqlResponse(BaseModel):
    data: object = None
    errors: list[_GraphqlError] = Field(default_factory=list)


class _Author(BaseModel):
    email: str


class _Authors(BaseModel):
    page_info: _PageInfo = Field(alias="pageInfo")
    nodes: list[_Author]

    @model_validator(mode="after")
    def validate_complete_authors(self) -> Self:
        if self.page_info.has_next_page:
            raise ValueError("a commit requires its complete author list")
        return self


class _Commit(BaseModel):
    additions: int = Field(strict=True, ge=0)
    authors: _Authors


class _History(BaseModel):
    page_info: _PageInfo = Field(alias="pageInfo")
    nodes: list[_Commit]


class _Target(BaseModel):
    history: _History


class _Branch(BaseModel):
    target: _Target


class _RepositoryCommits(BaseModel):
    default_branch: _Branch | None = Field(alias="defaultBranchRef")


class _CommitsData(BaseModel):
    node: _RepositoryCommits


async def _query(
    http_client: httpx.AsyncClient, query: str, variables: dict[str, str | None]
) -> object:
    response = await http_client.post(_GRAPHQL_URL, json={"query": query, "variables": variables})
    response.raise_for_status()
    try:
        result = _GraphqlResponse.model_validate(response.json())
    except (JSONDecodeError, ValidationError) as error:
        raise GithubRequestError("GitHub returned an invalid GraphQL response") from error
    if result.errors or result.data is None:
        raise GithubRequestError("GitHub could not complete the profile lookup")
    return result.data


async def _fetch_repository_agentic_commits(
    http_client: httpx.AsyncClient, repository_id: str
) -> list[AgenticCommit]:
    agentic_commits: list[AgenticCommit] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    while True:
        variables = {"repositoryId": repository_id, "since": _COMMITS_SINCE, "cursor": cursor}
        try:
            data = _CommitsData.model_validate(await _query(http_client, _COMMITS_QUERY, variables))
        except ValidationError as error:
            raise GithubRequestError("GitHub returned invalid commit data") from error
        if data.node.default_branch is None:
            return agentic_commits
        history = data.node.default_branch.target.history
        for commit in history.nodes:
            agent = find_agent(author.email for author in commit.authors.nodes)
            if agent is not None:
                agentic_commits.append(AgenticCommit(agent, commit.additions))
        if not history.page_info.has_next_page:
            return agentic_commits
        next_cursor = history.page_info.end_cursor
        if next_cursor is None or next_cursor in seen_cursors:
            raise GithubRequestError("GitHub returned an invalid commit pagination cursor")
        seen_cursors.add(next_cursor)
        cursor = next_cursor


async def _fetch_repositories(
    http_client: httpx.AsyncClient, login: VerifiedGithubUsername
) -> _User:
    repositories: list[_Repository] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    while True:
        try:
            data = _UserData.model_validate(
                await _query(http_client, _REPOSITORIES_QUERY, {"login": login, "cursor": cursor})
            )
        except ValidationError as error:
            raise GithubRequestError("GitHub returned invalid repository data") from error
        if data.user is None:
            raise ProfileNotFoundError(f"no GitHub user named {login!r}")
        page = data.user.repositories
        repositories.extend(
            repository
            for repository in page.nodes
            if repository.pushed_at is not None and repository.pushed_at >= _COMMITS_SINCE
        )
        if not page.page_info.has_next_page or any(
            repository.pushed_at is not None and repository.pushed_at < _COMMITS_SINCE
            for repository in page.nodes
        ):
            return _User(
                databaseId=data.user.database_id,
                repositories=_Repositories(pageInfo=page.page_info, nodes=repositories),
            )
        next_cursor = page.page_info.end_cursor
        if next_cursor is None or next_cursor in seen_cursors:
            raise GithubRequestError("GitHub returned an invalid repository pagination cursor")
        seen_cursors.add(next_cursor)
        cursor = next_cursor


async def fetch_github_profile(token: str, login: VerifiedGithubUsername) -> GithubProfile:
    """Post: all agentic commits since 2025 across public non-fork repositories,
    or ProfileNotFoundError. Incomplete GitHub responses raise GithubRequestError."""
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx.Timeout(_TIMEOUT_SECONDS, pool=None),
        limits=httpx.Limits(max_connections=_MAXIMUM_CONNECTIONS),
    ) as http_client:
        user = await _fetch_repositories(http_client, login)
        agentic_commits_by_repository = await asyncio.gather(
            *(
                _fetch_repository_agentic_commits(http_client, repository.id)
                for repository in user.repositories.nodes
            )
        )
    return GithubProfile(
        GithubUserId(user.database_id),
        login,
        tuple(chain.from_iterable(agentic_commits_by_repository)),
    )
