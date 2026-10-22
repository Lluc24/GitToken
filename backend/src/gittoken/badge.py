from dataclasses import dataclass

from jinja2 import Environment, PackageLoader, StrictUndefined

from gittoken.domain import NAME_BY_AGENT, Agent

_MAX_ROWS = 2


@dataclass(frozen=True)
class _Row:
    mark: str
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


def _row(mark: str, name: str, tokens: int, total_tokens: int) -> _Row:
    share = tokens / total_tokens if total_tokens else 0
    return _Row(mark=mark, name=name, tokens=tokens, share=share, percent=round(share * 100))


def _rows(tokens_by_agent: dict[Agent, int], total_tokens: int) -> list[_Row]:
    """Post: up to two agents by name; beyond that, the top agent plus the rest folded into Others."""
    agents = sorted(tokens_by_agent.items(), key=lambda item: item[1], reverse=True)
    rows = [_row(agent, NAME_BY_AGENT[agent], tokens, total_tokens) for agent, tokens in agents]
    if len(rows) > _MAX_ROWS:
        others_tokens = sum(row.tokens for row in rows[1:])
        return [rows[0], _row("others", "Others", others_tokens, total_tokens)]
    return rows


def render_badge(
    login: str,
    total_tokens: int,
    tokens_by_agent: dict[Agent, int],
    rarity: str,
) -> str:
    return _template.render(
        login=login,
        total_tokens=total_tokens,
        rarity=rarity,
        rows=_rows(tokens_by_agent, total_tokens),
    )
