import re

from gittoken.domain.agent import Agent
from gittoken.domain.commit import Commit
from gittoken.domain.github_login import GithubLogin

# Lowercase emails each agent leaves as the commit author or in a Co-authored-by trailer.
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

_COAUTHOR_EMAIL = re.compile(r"^co-authored-by:.*<([^<>\s]+)>\s*$", re.IGNORECASE | re.MULTILINE)


def find_agent(commit: Commit, owner: GithubLogin) -> Agent | None:
    """Pre: commit is in a repository owner owns.
    Post: the agent that authored the commit, or co-authored a commit owner authored; None otherwise."""
    authoring_agent = AGENT_BY_EMAIL.get(commit.author_email.lower())
    if authoring_agent is not None:
        return authoring_agent
    if commit.author_login is None or commit.author_login.lower() != owner.value.lower():
        return None
    for coauthor_email in _COAUTHOR_EMAIL.findall(commit.message):
        if coauthor_email.lower() in AGENT_BY_EMAIL:
            return AGENT_BY_EMAIL[coauthor_email.lower()]
    return None
