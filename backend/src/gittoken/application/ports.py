from datetime import datetime
from typing import Protocol

from gittoken.domain.agentic_commit import AgenticCommit


class ProfileNotFoundError(Exception):
    pass


class AgenticCommitSource(Protocol):
    async def list_agentic_commits(self, login: str, since: datetime) -> list[AgenticCommit]:
        """Post: the agentic commits since `since` in the public non-fork repositories login owns,
        or ProfileNotFoundError."""
        ...
