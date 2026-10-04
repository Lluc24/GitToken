from dataclasses import dataclass

from gittoken.domain.agent import Agent


@dataclass(frozen=True)
class AgenticCommit:
    agent: Agent
    lines_added: int
