from pathlib import Path

import yaml
from pydantic import TypeAdapter

from gittoken.domain.agent import Agent

_EMAILS_BY_AGENT = TypeAdapter(dict[Agent, list[str]])


def load_agent_by_email(signatures_file: Path) -> dict[str, Agent]:
    """Post: keys are lowercase."""
    emails_by_agent = _EMAILS_BY_AGENT.validate_python(yaml.safe_load(signatures_file.read_text()))
    return {email.lower(): agent for agent, emails in emails_by_agent.items() for email in emails}
