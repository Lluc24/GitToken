import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from gittoken.domain.agent import Agent
from gittoken.domain.commit import Commit
from gittoken.domain.github_login import GithubLogin


class SignalKind(StrEnum):
    COAUTHOR_EMAIL = "coauthor_email"
    AUTHOR_LOGIN = "author_login"
    AUTHOR_EMAIL = "author_email"


class SignatureValueNotLowercaseError(ValueError):
    pass


@dataclass(frozen=True)
class AgentSignature:
    agent: Agent
    kind: SignalKind
    value: str

    def __post_init__(self) -> None:
        if self.value != self.value.lower():
            raise SignatureValueNotLowercaseError(f"expected a lowercase signature value, got {self.value!r}")


@dataclass(frozen=True)
class Attribution:
    agent: Agent
    kind: SignalKind


_COAUTHOR_EMAIL = re.compile(r"^co-authored-by:.*<([^<>\s]+)>\s*$", re.IGNORECASE | re.MULTILINE)


def _signal_values(commit: Commit, kind: SignalKind) -> frozenset[str]:
    match kind:
        case SignalKind.COAUTHOR_EMAIL:
            return frozenset(email.lower() for email in _COAUTHOR_EMAIL.findall(commit.message))
        case SignalKind.AUTHOR_EMAIL:
            return frozenset({commit.author_email.lower()})
        case SignalKind.AUTHOR_LOGIN:
            if commit.author_login is None:
                return frozenset()
            return frozenset({commit.author_login.lower()})


def attribute_commit(commit: Commit, signatures: Sequence[AgentSignature]) -> Attribution | None:
    """Pre: signatures are ordered by precedence.
    Post: the attribution of the first matching signature, or None when the commit carries no agent signal."""
    for signature in signatures:
        if signature.value in _signal_values(commit, signature.kind):
            return Attribution(signature.agent, signature.kind)
    return None


def is_credited_to_repository_owner(commit: Commit, attribution: Attribution, owner: GithubLogin) -> bool:
    """Pre: commit belongs to a repository owned by owner.
    Post: True when the agent itself authored the commit, or co-authored a commit the owner authored."""
    if attribution.kind is not SignalKind.COAUTHOR_EMAIL:
        return True
    return commit.author_login is not None and commit.author_login.lower() == owner.value.lower()
