from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import NewType


class Agent(StrEnum):
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    COPILOT = "copilot"
    CURSOR = "cursor"
    DEVIN = "devin"
    JULES = "jules"
    AIDER = "aider"


# Lowercase emails each agent leaves as a commit author or co-author.
AGENT_BY_EMAIL = {
    "noreply@anthropic.com": Agent.CLAUDE_CODE,
    "noreply@openai.com": Agent.CODEX,
    "199175422+chatgpt-codex-connector[bot]@users.noreply.github.com": Agent.CODEX,
    "cursoragent@cursor.com": Agent.CURSOR,
    "agent@cursor.com": Agent.CURSOR,
    "198982749+copilot@users.noreply.github.com": Agent.COPILOT,
    "223556219+copilot@users.noreply.github.com": Agent.COPILOT,
    "158243242+devin-ai-integration[bot]@users.noreply.github.com": Agent.DEVIN,
    "161369871+google-labs-jules[bot]@users.noreply.github.com": Agent.JULES,
    "aider@aider.chat": Agent.AIDER,
    "noreply@aider.chat": Agent.AIDER,
}


def find_agent(author_emails: Iterable[str]) -> Agent | None:
    """Post: the first agent among a commit's authors and co-authors, or None for a commit with no agent."""
    for author_email in author_emails:
        if author_email.lower() in AGENT_BY_EMAIL:
            return AGENT_BY_EMAIL[author_email.lower()]
    return None


# v0 guess: ~30 output tokens per added line, ~100 input tokens (mostly cache reads) per output token.
TOKENS_PER_ADDED_LINE = 3000


@dataclass(frozen=True)
class AgenticCommit:
    agent: Agent
    lines_added: int

    @property
    def tokens(self) -> int:
        return self.lines_added * TOKENS_PER_ADDED_LINE


class Rarity(StrEnum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    CHAMPION = "champion"


# v0 guess, lowest first: each tier is ten times the previous one (~3.3k added lines for rare).
MIN_TOKENS_BY_RARITY = {
    Rarity.COMMON: 0,
    Rarity.RARE: 10_000_000,
    Rarity.EPIC: 100_000_000,
    Rarity.LEGENDARY: 1_000_000_000,
    Rarity.CHAMPION: 10_000_000_000,
}


class ProfileNotFoundError(Exception):
    pass


# A username that passed the format check at the boundary.
VerifiedGithubUsername = NewType("VerifiedGithubUsername", str)

# GitHub's immutable numeric user id; logins can be renamed.
GithubUserId = NewType("GithubUserId", int)


@dataclass(frozen=True)
class GithubProfile:
    github_id: GithubUserId
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

    @property
    def rarity(self) -> Rarity:
        """Post: the highest rarity whose minimum the total tokens reach."""
        reached_rarities = [
            rarity
            for rarity, min_tokens in MIN_TOKENS_BY_RARITY.items()
            if self.total_tokens >= min_tokens
        ]
        return reached_rarities[-1]
