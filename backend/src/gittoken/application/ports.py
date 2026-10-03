from datetime import datetime
from typing import Protocol

from gittoken.domain.commit import Commit
from gittoken.domain.github_login import GithubLogin
from gittoken.domain.repository import Repository


class ProfileNotFoundError(Exception):
    pass


class GithubCommitSource(Protocol):
    async def list_owned_public_repositories(self, login: GithubLogin) -> list[Repository]:
        """Post: the public non-fork repositories login owns, or ProfileNotFoundError."""
        ...

    async def list_default_branch_commits(self, repository: Repository, since: datetime) -> list[Commit]: ...
