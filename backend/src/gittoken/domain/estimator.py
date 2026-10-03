from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from gittoken.domain.agent import Agent
from gittoken.domain.attribution import find_agent
from gittoken.domain.commit import Commit
from gittoken.domain.github_login import GithubLogin

# v0 guess: ~30 output tokens per added line, ~100 input tokens (mostly cache reads) per output token.
TOKENS_PER_ADDED_LINE = 3000


@dataclass(frozen=True)
class AgentEstimate:
    agent: Agent
    lines_added: int

    @property
    def tokens(self) -> int:
        return self.lines_added * TOKENS_PER_ADDED_LINE


@dataclass(frozen=True)
class ProfileEstimate:
    login: GithubLogin
    agent_estimates: tuple[AgentEstimate, ...]

    @property
    def total_tokens(self) -> int:
        return sum(agent_estimate.tokens for agent_estimate in self.agent_estimates)


def estimate_profile(owner: GithubLogin, commits: Iterable[Commit]) -> ProfileEstimate:
    """Pre: commits are in repositories owner owns.
    Post: one estimate per agent with at least one commit, largest first."""
    lines_added_by_agent: Counter[Agent] = Counter()
    for commit in commits:
        agent = find_agent(commit, owner)
        if agent is not None:
            lines_added_by_agent[agent] += commit.lines_added
    return ProfileEstimate(
        login=owner,
        agent_estimates=tuple(
            AgentEstimate(agent, lines_added) for agent, lines_added in lines_added_by_agent.most_common()
        ),
    )
