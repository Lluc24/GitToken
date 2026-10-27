from base64 import b64encode
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO

from jinja2 import Environment, PackageLoader, StrictUndefined
from PIL import Image

from gittoken.domain import NAME_BY_AGENT, Agent, Avatar

_MAX_ROWS = 2
_AVATAR_JPEG_QUALITY = 82


class Theme(StrEnum):
    DARK = "dark"
    LIGHT = "light"


@dataclass(frozen=True)
class ProfileStats:
    login: str
    total_tokens: int
    tokens_by_agent: dict[Agent, int]
    rarity: str


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
_badge_template = _environment.get_template("badge.svg.jinja")
_profile_template = _environment.get_template("profile.svg.jinja")
_notice_template = _environment.get_template("notice.svg.jinja")


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


def render_badge(stats: ProfileStats, theme: Theme) -> str:
    return _badge_template.render(
        login=stats.login,
        total_tokens=stats.total_tokens,
        rarity=stats.rarity,
        theme=theme,
        rows=_rows(stats.tokens_by_agent, stats.total_tokens),
    )


def _avatar_data_url(avatar: Avatar) -> str:
    """Post: a JPEG data URL; GitHub serves some photos as PNGs several times larger."""
    jpeg = BytesIO()
    with Image.open(BytesIO(avatar)) as image:
        image.convert("RGB").save(jpeg, "JPEG", quality=_AVATAR_JPEG_QUALITY, optimize=True)
    return f"data:image/jpeg;base64,{b64encode(jpeg.getvalue()).decode()}"


def render_profile_card(stats: ProfileStats, avatar: Avatar, theme: Theme) -> str:
    """Post: a self-contained SVG; the avatar is inlined because READMEs block external images."""
    rows = _rows(stats.tokens_by_agent, stats.total_tokens)
    agents = ", ".join(f"{row.name} {_format_tokens(row.tokens)}" for row in rows)
    description = (
        f"{stats.login}: {_format_tokens(stats.total_tokens)} estimated tokens, {stats.rarity}"
    )
    return _profile_template.render(
        login=stats.login,
        total_tokens=stats.total_tokens,
        rarity=stats.rarity,
        theme=theme,
        rows=rows,
        description=f"{description}. {agents}." if rows else f"{description}.",
        avatar_url=_avatar_data_url(avatar),
    )


def render_scanning_card(login: str, theme: Theme) -> str:
    """Post: a placeholder shown while the first scan of a profile is still running."""
    return _notice_template.render(
        login=login,
        message="Scanning public commits, back in a minute",
        is_pending=True,
        theme=theme,
    )


def render_error_card(login: str, message: str, theme: Theme) -> str:
    """Post: a card explaining why the badge could not be drawn; READMEs show it instead of a broken image."""
    return _notice_template.render(login=login, message=message, is_pending=False, theme=theme)
