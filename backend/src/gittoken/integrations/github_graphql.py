import asyncio
from datetime import datetime
from itertools import chain
from typing import Any

import httpx
from pydantic import AwareDatetime, BaseModel, Field

from gittoken.application.ports import ProfileNotFoundError
from gittoken.domain.agentic_commit import AgenticCommit
from gittoken.domain.attribution import find_agent

_GRAPHQL_URL = "https://api.github.com/graphql"
_NOT_FOUND_ERROR_TYPE = "NOT_FOUND"

_REPOSITORIES_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      pageInfo { hasNextPage endCursor }
      nodes { name owner { login } pushedAt }
    }
  }
}
"""

_COMMITS_QUERY = """
query($owner: String!, $name: String!, $since: GitTimestamp!, $cursor: String) {
  repository(owner: $owner, name: $name) {
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
"""


class GithubApiError(Exception):
    pass


class _Error(BaseModel):
    type: str | None = None
    message: str


class _Envelope(BaseModel):
    data: dict[str, Any] | None = None
    errors: list[_Error] = []


class _PageInfo(BaseModel):
    has_next_page: bool = Field(alias="hasNextPage")
    end_cursor: str | None = Field(alias="endCursor")


class _Owner(BaseModel):
    login: str


class _RepositoryNode(BaseModel):
    name: str
    owner: _Owner
    pushed_at: AwareDatetime | None = Field(alias="pushedAt")


class _Repositories(BaseModel):
    page_info: _PageInfo = Field(alias="pageInfo")
    nodes: list[_RepositoryNode]


class _User(BaseModel):
    repositories: _Repositories


class _RepositoriesData(BaseModel):
    user: _User | None


class _Author(BaseModel):
    email: str


class _Authors(BaseModel):
    nodes: list[_Author]


class _CommitNode(BaseModel):
    additions: int
    authors: _Authors


class _History(BaseModel):
    page_info: _PageInfo = Field(alias="pageInfo")
    nodes: list[_CommitNode]


class _Target(BaseModel):
    history: _History


class _Ref(BaseModel):
    target: _Target


class _CommitsRepository(BaseModel):
    default_branch_ref: _Ref | None = Field(alias="defaultBranchRef")


class _CommitsData(BaseModel):
    repository: _CommitsRepository


def _agentic_commits(nodes: list[_CommitNode]) -> list[AgenticCommit]:
    agentic_commits = []
    for node in nodes:
        agent = find_agent(author.email for author in node.authors.nodes)
        if agent is not None:
            agentic_commits.append(AgenticCommit(agent, node.additions))
    return agentic_commits


class GithubGraphqlClient:
    """Pre: http_client has explicit timeouts."""

    def __init__(self, http_client: httpx.AsyncClient, token: str, maximum_concurrent_requests: int) -> None:
        self._http_client = http_client
        self._token = token
        self._request_slots = asyncio.Semaphore(maximum_concurrent_requests)

    async def _query(self, query: str, variables: dict[str, str | None]) -> dict[str, Any]:
        async with self._request_slots:
            response = await self._http_client.post(
                _GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers={"Authorization": f"Bearer {self._token}"},
            )
        response.raise_for_status()
        envelope = _Envelope.model_validate_json(response.content)
        unexpected_errors = [error for error in envelope.errors if error.type != _NOT_FOUND_ERROR_TYPE]
        if envelope.data is None or unexpected_errors:
            raise GithubApiError(f"GitHub GraphQL query failed: {envelope.errors}")
        return envelope.data

    async def _list_repositories_pushed_since(self, login: str, since: datetime) -> list[_RepositoryNode]:
        repositories: list[_RepositoryNode] = []
        cursor: str | None = None
        while True:
            data = _RepositoriesData.model_validate(
                await self._query(_REPOSITORIES_QUERY, {"login": login, "cursor": cursor})
            )
            if data.user is None:
                raise ProfileNotFoundError(f"no GitHub user named {login!r}")
            page = data.user.repositories
            repositories.extend(node for node in page.nodes if node.pushed_at is not None and node.pushed_at >= since)
            if not page.page_info.has_next_page:
                return repositories
            cursor = page.page_info.end_cursor

    async def _list_repository_agentic_commits(
        self, repository: _RepositoryNode, since: datetime
    ) -> list[AgenticCommit]:
        agentic_commits: list[AgenticCommit] = []
        cursor: str | None = None
        while True:
            data = _CommitsData.model_validate(
                await self._query(
                    _COMMITS_QUERY,
                    {
                        "owner": repository.owner.login,
                        "name": repository.name,
                        "since": since.isoformat(),
                        "cursor": cursor,
                    },
                )
            )
            if data.repository.default_branch_ref is None:
                return agentic_commits
            history = data.repository.default_branch_ref.target.history
            agentic_commits.extend(_agentic_commits(history.nodes))
            if not history.page_info.has_next_page:
                return agentic_commits
            cursor = history.page_info.end_cursor

    async def list_agentic_commits(self, login: str, since: datetime) -> list[AgenticCommit]:
        repositories = await self._list_repositories_pushed_since(login, since)
        agentic_commits_by_repository = await asyncio.gather(
            *(self._list_repository_agentic_commits(repository, since) for repository in repositories)
        )
        return list(chain.from_iterable(agentic_commits_by_repository))
