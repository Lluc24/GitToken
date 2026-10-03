from collections.abc import Sequence
from datetime import datetime

from gittoken.application.ports import GithubCommitSource
from gittoken.domain.attribution import (
    AgentSignature,
    Attribution,
    attribute_commit,
    is_credited_to_repository_owner,
)
from gittoken.domain.commit import Commit
from gittoken.domain.estimator import ProfileEstimate, estimate_profile
from gittoken.domain.github_login import GithubLogin


class EstimateProfileTokens:
    def __init__(
        self,
        github: GithubCommitSource,
        signatures: Sequence[AgentSignature],
        commits_since: datetime,
    ) -> None:
        self._github = github
        self._signatures = signatures
        self._commits_since = commits_since

    async def execute(self, login: GithubLogin) -> ProfileEstimate:
        attributed_commits: list[tuple[Commit, Attribution]] = []
        for repository in await self._github.list_owned_public_repositories(login):
            if repository.pushed_at < self._commits_since:
                continue
            for commit in await self._github.list_default_branch_commits(repository, self._commits_since):
                attribution = attribute_commit(commit, self._signatures)
                if attribution is not None and is_credited_to_repository_owner(commit, attribution, login):
                    attributed_commits.append((commit, attribution))
        return estimate_profile(login, attributed_commits)
