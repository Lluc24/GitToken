from dataclasses import dataclass

from jinja2 import Environment, PackageLoader, StrictUndefined

from gittoken.domain import NAME_BY_AGENT, Agent

_MAX_ROWS = 4


@dataclass(frozen=True)
class _AgentRow:
    agent: Agent
    name: str
    tokens: int
    share: float
    percent: int


def _format_tokens(tokens: int) -> str:
    for threshold, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if tokens >= threshold:
            text = f"{tokens / threshold:.1f}".rstrip("0").rstrip(".")
            return f"{text}{suffix}"
    return str(tokens)


_environment = Environment(
    loader=PackageLoader("gittoken"),
    autoescape=True,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
_environment.filters["compact_tokens"] = _format_tokens
_template = _environment.get_template("badge.svg")


def render_badge(
    login: str,
    total_tokens: int,
    tokens_by_agent: dict[Agent, int],
    rarity: str,
) -> str:
    agents = sorted(tokens_by_agent.items(), key=lambda item: item[1], reverse=True)
    rows = [
        _AgentRow(
            agent=agent,
            name=NAME_BY_AGENT[agent],
            tokens=tokens,
            share=tokens / total_tokens if total_tokens else 0,
            percent=round(tokens / total_tokens * 100) if total_tokens else 0,
        )
        for agent, tokens in agents[:_MAX_ROWS]
    ]
    return _template.render(
        login=login,
        total_tokens=total_tokens,
        rarity=rarity,
        rows=rows,
        hidden_agent_count=len(agents) - len(rows),
    )
