from collections import Counter
from collections.abc import Iterable, Mapping
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
    commit_count: int
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


def estimate_profile(
    owner: GithubLogin, commits: Iterable[Commit], agent_by_email: Mapping[str, Agent]
) -> ProfileEstimate:
    """Pre: commits are in repositories owner owns.
    Post: one estimate per agent with at least one commit, largest first."""
    commit_count_by_agent: Counter[Agent] = Counter()
    lines_added_by_agent: Counter[Agent] = Counter()
    for commit in commits:
        agent = find_agent(commit, owner, agent_by_email)
        if agent is not None:
            commit_count_by_agent[agent] += 1
            lines_added_by_agent[agent] += commit.lines_added
    return ProfileEstimate(
        login=owner,
        agent_estimates=tuple(
            AgentEstimate(agent, commit_count_by_agent[agent], lines_added)
            for agent, lines_added in lines_added_by_agent.most_common()
        ),
    )
