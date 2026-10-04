from collections import Counter
from dataclasses import dataclass
from typing import NewType

from gittoken.domain.agent import Agent
from gittoken.domain.agentic_commit import AgenticCommit

# A username that passed the format check at the boundary.
VerifiedGithubUsername = NewType("VerifiedGithubUsername", str)


@dataclass(frozen=True)
class GithubProfile:
    login: VerifiedGithubUsername
    agentic_commits: tuple[AgenticCommit, ...]

    @property
    def total_tokens(self) -> int:
        return sum(agentic_commit.tokens for agentic_commit in self.agentic_commits)

    @property
    def tokens_by_agent(self) -> dict[Agent, int]:
        """Post: agents with at least one commit, largest first."""
        tokens_by_agent: Counter[Agent] = Counter()
        for agentic_commit in self.agentic_commits:
            tokens_by_agent[agentic_commit.agent] += agentic_commit.tokens
        return dict(tokens_by_agent.most_common())
