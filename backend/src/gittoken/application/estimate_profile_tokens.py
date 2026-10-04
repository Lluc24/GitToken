from datetime import datetime

from gittoken.application.ports import AgenticCommitSource
from gittoken.domain.github_profile import GithubProfile


class EstimateProfileTokens:
    def __init__(self, github: AgenticCommitSource, commits_since: datetime) -> None:
        self._github = github
        self._commits_since = commits_since

    async def execute(self, login: str) -> GithubProfile:
        return GithubProfile(login, tuple(await self._github.list_agentic_commits(login, self._commits_since)))
