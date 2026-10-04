from collections.abc import Iterable

from gittoken.domain.agent import Agent

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
