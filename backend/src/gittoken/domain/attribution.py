import re
from collections.abc import Mapping

from gittoken.domain.agent import Agent
from gittoken.domain.commit import Commit
from gittoken.domain.github_login import GithubLogin

_COAUTHOR_EMAIL = re.compile(r"^co-authored-by:.*<([^<>\s]+)>\s*$", re.IGNORECASE | re.MULTILINE)


def find_agent(commit: Commit, owner: GithubLogin, agent_by_email: Mapping[str, Agent]) -> Agent | None:
    """Pre: commit is in a repository owner owns; agent_by_email keys are lowercase.
    Post: the agent that authored the commit, or co-authored a commit owner authored; None otherwise."""
    authoring_agent = agent_by_email.get(commit.author_email.lower())
    if authoring_agent is not None:
        return authoring_agent
    if commit.author_login is None or commit.author_login.lower() != owner.value.lower():
        return None
    for coauthor_email in _COAUTHOR_EMAIL.findall(commit.message):
        if coauthor_email.lower() in agent_by_email:
            return agent_by_email[coauthor_email.lower()]
    return None
