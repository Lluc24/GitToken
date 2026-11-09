from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import StrEnum
from types import MappingProxyType
from typing import NewType


class Agent(StrEnum):
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    COPILOT = "copilot"
    CURSOR = "cursor"
    DEVIN = "devin"
    JULES = "jules"
    AIDER = "aider"


NAME_BY_AGENT = {
    Agent.CLAUDE_CODE: "Claude Code",
    Agent.CODEX: "Codex",
    Agent.COPILOT: "Copilot",
    Agent.CURSOR: "Cursor",
    Agent.DEVIN: "Devin",
    Agent.JULES: "Jules",
    Agent.AIDER: "Aider",
}


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


def estimate_tokens(lines_added: int) -> int:
    return lines_added * TOKENS_PER_ADDED_LINE


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


def rarity_for(total_tokens: int) -> Rarity:
    """Post: the highest rarity whose minimum total_tokens reaches."""
    reached_rarities = [
        rarity for rarity, min_tokens in MIN_TOKENS_BY_RARITY.items() if total_tokens >= min_tokens
    ]
    return reached_rarities[-1]


class GithubRequestError(Exception):
    pass


class ProfileNotFoundError(Exception):
    pass


class ProfileStoreError(Exception):
    pass


class SlackNotificationError(Exception):
    pass


class InvalidWebhookError(Exception):
    pass


class InstallationNotFoundError(Exception):
    pass


class OrganizationInstallationError(Exception):
    pass


class InvalidAuthorizationCodeError(Exception):
    pass


GITHUB_LOGIN_PATTERN = "^[A-Za-z0-9][A-Za-z0-9-]{0,38}$"

# A username that passed the format check at the boundary.
VerifiedGithubUsername = NewType("VerifiedGithubUsername", str)

# Image bytes that GitHub served with a PNG, JPEG or GIF media type.
Avatar = NewType("Avatar", bytes)

# GitHub's immutable numeric user id; logins can be renamed.
GithubUserId = NewType("GithubUserId", int)


# GitHub's id for one account's installation of the GitHub App.
InstallationId = NewType("InstallationId", int)


@dataclass(frozen=True)
class PersonalInstallation:
    github_id: GithubUserId
    login: VerifiedGithubUsername


# A one-time code GitHub hands the browser when a user authorizes the app during installation.
GithubAuthorizationCode = NewType("GithubAuthorizationCode", str)


@dataclass(frozen=True)
class InstallationAuthorization:
    installation_id: InstallationId
    code: GithubAuthorizationCode


# GitHub's immutable numeric repository id; names are never stored.
RepositoryId = NewType("RepositoryId", int)


@dataclass(frozen=True)
class PrivateRepository:
    repository_id: RepositoryId
    lines_added_by_agent: MappingProxyType[Agent, int]


@dataclass(frozen=True)
class AccountDisconnected:
    github_id: GithubUserId


@dataclass(frozen=True)
class RepositoriesRevoked:
    repository_ids: tuple[RepositoryId, *tuple[RepositoryId, ...]]


# An account took back access, so the private repositories it covered must be forgotten.
type ConsentWithdrawal = AccountDisconnected | RepositoriesRevoked


@dataclass(frozen=True)
class GithubProfile:
    github_id: GithubUserId
    login: VerifiedGithubUsername
    public_lines_added_by_agent: MappingProxyType[Agent, int]
    private_repositories: tuple[PrivateRepository, ...]

    @property
    def lines_added_by_agent(self) -> dict[Agent, int]:
        """Post: public and private lines added, summed per agent."""
        lines_added_by_agent = Counter(self.public_lines_added_by_agent)
        for private_repository in self.private_repositories:
            lines_added_by_agent.update(private_repository.lines_added_by_agent)
        return dict(lines_added_by_agent)

    @property
    def includes_private_repositories(self) -> bool:
        return len(self.private_repositories) > 0

    @property
    def total_tokens(self) -> int:
        return estimate_tokens(sum(self.lines_added_by_agent.values()))

    @property
    def tokens_by_agent(self) -> dict[Agent, int]:
        """Post: agents with at least one commit, largest first, ties by agent."""
        return {
            agent: estimate_tokens(lines_added)
            for agent, lines_added in sorted(
                self.lines_added_by_agent.items(), key=lambda item: (-item[1], item[0])
            )
        }

    @property
    def rarity(self) -> Rarity:
        return rarity_for(self.total_tokens)


def without_withdrawn_repositories(
    profile: GithubProfile, withdrawal: ConsentWithdrawal
) -> GithubProfile:
    """Post: the profile without the private repositories the withdrawal covers."""
    match withdrawal:
        case AccountDisconnected():
            kept_repositories: tuple[PrivateRepository, ...] = ()
        case RepositoriesRevoked(repository_ids):
            kept_repositories = tuple(
                private_repository
                for private_repository in profile.private_repositories
                if private_repository.repository_id not in repository_ids
            )
    return replace(profile, private_repositories=kept_repositories)


@dataclass(frozen=True)
class LeaderboardEntry:
    login: VerifiedGithubUsername
    total_tokens: int

    @property
    def rarity(self) -> Rarity:
        return rarity_for(self.total_tokens)
