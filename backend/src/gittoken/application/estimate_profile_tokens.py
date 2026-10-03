import asyncio
from collections.abc import Mapping
from datetime import datetime
from itertools import chain

from gittoken.application.ports import GithubCommitSource
from gittoken.domain.agent import Agent
from gittoken.domain.estimator import ProfileEstimate, estimate_profile
from gittoken.domain.github_login import GithubLogin


class EstimateProfileTokens:
    def __init__(
        self, github: GithubCommitSource, agent_by_email: Mapping[str, Agent], commits_since: datetime
    ) -> None:
        self._github = github
        self._agent_by_email = agent_by_email
        self._commits_since = commits_since

    async def execute(self, login: GithubLogin) -> ProfileEstimate:
        repositories = [
            repository
            for repository in await self._github.list_owned_public_repositories(login)
            if repository.pushed_at >= self._commits_since
        ]
        commits_by_repository = await asyncio.gather(
            *(self._github.list_default_branch_commits(repository, self._commits_since) for repository in repositories)
        )
        return estimate_profile(login, chain.from_iterable(commits_by_repository), self._agent_by_email)
