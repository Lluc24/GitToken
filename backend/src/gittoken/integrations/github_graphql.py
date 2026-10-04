import asyncio
from itertools import chain
from typing import Any

import httpx
from pydantic import BaseModel, Field

from gittoken.domain.agentic_commit import AgenticCommit
from gittoken.domain.attribution import find_agent
from gittoken.domain.github_profile import GithubProfile, ProfileNotFoundError, VerifiedGithubUsername

_GRAPHQL_URL = "https://api.github.com/graphql"
_TIMEOUT_SECONDS = 30
_MAXIMUM_CONNECTIONS = 8
# GitHub timestamps are UTC ISO 8601, so they compare correctly as strings.
_COMMITS_SINCE = "2025-01-01T00:00:00Z"

_REPOSITORIES_QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
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
              nodes { additions authors(first: 10) { nodes { email } } }
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


class _Repositories(BaseModel):
    nodes: list[_Repository]


class _User(BaseModel):
    repositories: _Repositories


class _UserData(BaseModel):
    user: _User | None


class _Author(BaseModel):
    email: str


class _Authors(BaseModel):
    nodes: list[_Author]


class _Commit(BaseModel):
    additions: int
    authors: _Authors


class _PageInfo(BaseModel):
    has_next_page: bool = Field(alias="hasNextPage")
    end_cursor: str | None = Field(alias="endCursor")


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


async def _query(http_client: httpx.AsyncClient, query: str, variables: dict[str, str | None]) -> Any:
    response = await http_client.post(_GRAPHQL_URL, json={"query": query, "variables": variables})
    response.raise_for_status()
    return response.json()["data"]


async def _fetch_repository_agentic_commits(http_client: httpx.AsyncClient, repository_id: str) -> list[AgenticCommit]:
    agentic_commits: list[AgenticCommit] = []
    cursor: str | None = None
    while True:
        variables = {"repositoryId": repository_id, "since": _COMMITS_SINCE, "cursor": cursor}
        data = _CommitsData.model_validate(await _query(http_client, _COMMITS_QUERY, variables))
        if data.node.default_branch is None:
            return agentic_commits
        history = data.node.default_branch.target.history
        for commit in history.nodes:
            agent = find_agent(author.email for author in commit.authors.nodes)
            if agent is not None:
                agentic_commits.append(AgenticCommit(agent, commit.additions))
        if not history.page_info.has_next_page:
            return agentic_commits
        cursor = history.page_info.end_cursor


async def fetch_github_profile(token: str, login: VerifiedGithubUsername) -> GithubProfile:
    """Post: the profile with the agentic commits of its 100 most recently pushed public non-fork repositories,
    or ProfileNotFoundError."""
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx.Timeout(_TIMEOUT_SECONDS, pool=None),
        limits=httpx.Limits(max_connections=_MAXIMUM_CONNECTIONS),
    ) as http_client:
        data = _UserData.model_validate(await _query(http_client, _REPOSITORIES_QUERY, {"login": login}))
        if data.user is None:
            raise ProfileNotFoundError(f"no GitHub user named {login!r}")
        agentic_commits_by_repository = await asyncio.gather(
            *(
                _fetch_repository_agentic_commits(http_client, repository.id)
                for repository in data.user.repositories.nodes
                if repository.pushed_at is not None and repository.pushed_at >= _COMMITS_SINCE
            )
        )
    return GithubProfile(login, tuple(chain.from_iterable(agentic_commits_by_repository)))
