from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from gittoken.domain.agent import Agent
from gittoken.domain.attribution import Attribution
from gittoken.domain.commit import Commit
from gittoken.domain.github_login import GithubLogin


@dataclass(frozen=True)
class EstimatorVersion:
    version: str
    tokens_per_added_line: int


@dataclass(frozen=True)
class AgentEstimate:
    agent: Agent
    commit_count: int
    lines_added: int
    tokens: int


@dataclass(frozen=True)
class ProfileEstimate:
    login: GithubLogin
    estimator_version: str
    agent_estimates: tuple[AgentEstimate, ...]

    @property
    def total_tokens(self) -> int:
        return sum(agent_estimate.tokens for agent_estimate in self.agent_estimates)


def estimate_profile(
    login: GithubLogin, attributed_commits: Sequence[tuple[Commit, Attribution]], version: EstimatorVersion
) -> ProfileEstimate:
    """Post: one estimate per agent with at least one commit, largest first."""
    commits_by_agent: defaultdict[Agent, list[Commit]] = defaultdict(list)
    for commit, attribution in attributed_commits:
        commits_by_agent[attribution.agent].append(commit)
    agent_estimates = []
    for agent, commits in commits_by_agent.items():
        lines_added = sum(commit.lines.added for commit in commits)
        agent_estimates.append(
            AgentEstimate(
                agent=agent,
                commit_count=len(commits),
                lines_added=lines_added,
                tokens=lines_added * version.tokens_per_added_line,
            )
        )
    return ProfileEstimate(
        login=login,
        estimator_version=version.version,
        agent_estimates=tuple(sorted(agent_estimates, key=lambda estimate: estimate.tokens, reverse=True)),
    )
