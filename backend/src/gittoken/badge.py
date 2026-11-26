import json
from base64 import b64encode
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from importlib.resources import files
from io import BytesIO

from jinja2 import Environment, PackageLoader, StrictUndefined, Template
from PIL import Image

from gittoken.domain import (
    DAYS_PER_WEEK,
    HEATMAP_WEEKS,
    NAME_BY_AGENT,
    Avatar,
    GithubProfile,
    heatmap,
)

_MAX_ROWS = 2
_PROFILE_NAME_MAX_LENGTH = 20
_HEATMAP_NAME_MAX_LENGTH = 24
_NOTICE_NAME_MAX_LENGTH = 20
_AVATAR_JPEG_QUALITY = 82


class Theme(StrEnum):
    DARK = "dark"
    LIGHT = "light"


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


def _shortened_login(login: str, max_length: int) -> str:
    """Post: login if it fits in max_length characters, else its start and an ellipsis in max_length."""
    return login if len(login) <= max_length else f"{login[: max_length - 1]}…"


_environment = Environment(
    loader=PackageLoader("gittoken"),
    autoescape=True,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
_environment.filters["compact_tokens"] = _format_tokens
_environment.globals["palette_file"] = json.loads(
    files("gittoken").joinpath("templates/palette.json").read_text(encoding="utf-8")
)
_badge_template = _environment.get_template("badge.svg.jinja")
_profile_template = _environment.get_template("profile.svg.jinja")
_wide_profile_template = _environment.get_template("wide_profile.svg.jinja")
_notice_template = _environment.get_template("notice.svg.jinja")
_heatmap_template = _environment.get_template("heatmap.svg.jinja")


def _row(mark: str, name: str, tokens: int, total_tokens: int) -> _Row:
    share = tokens / total_tokens if total_tokens else 0
    return _Row(mark=mark, name=name, tokens=tokens, share=share, percent=round(share * 100))


def _rows(profile: GithubProfile) -> list[_Row]:
    """Post: up to two agents by name; beyond that, the top agent plus the rest folded into Others."""
    total_tokens = profile.total_tokens
    rows = [
        _row(agent, NAME_BY_AGENT[agent], tokens, total_tokens)
        for agent, tokens in profile.tokens_by_agent.items()
    ]
    if len(rows) > _MAX_ROWS:
        others_tokens = sum(row.tokens for row in rows[1:])
        return [rows[0], _row("others", "Others", others_tokens, total_tokens)]
    return rows


def render_badge(profile: GithubProfile, theme: Theme) -> str:
    return _badge_template.render(
        login=profile.login,
        description=f"{profile.login}: {profile.total_tokens:,} estimated tokens, {profile.rarity}",
        total_tokens=profile.total_tokens,
        rarity=profile.rarity,
        theme=theme,
        rows=_rows(profile),
    )


def render_heatmap(profile: GithubProfile, theme: Theme, today: date) -> str:
    activity_heatmap = heatmap(profile, today)
    commits_text = f"{activity_heatmap.agent_commits:,} agent commits"
    return _heatmap_template.render(
        name=_shortened_login(profile.login, _HEATMAP_NAME_MAX_LENGTH),
        description=f"{profile.login}: {activity_heatmap.total_tokens:,} estimated tokens in {commits_text} over the last year",
        caption=f"tokens across {commits_text} in the last year",
        theme=theme,
        weeks=HEATMAP_WEEKS,
        days_per_week=DAYS_PER_WEEK,
        cells=activity_heatmap.cells,
        month_labels=activity_heatmap.month_labels,
        total_tokens=activity_heatmap.total_tokens,
    )


def _avatar_data_url(avatar: Avatar) -> str:
    """Post: a JPEG data URL; GitHub serves some photos as PNGs several times larger."""
    jpeg = BytesIO()
    with Image.open(BytesIO(avatar)) as image:
        image.convert("RGB").save(jpeg, "JPEG", quality=_AVATAR_JPEG_QUALITY, optimize=True)
    return f"data:image/jpeg;base64,{b64encode(jpeg.getvalue()).decode()}"


def _render_profile_layout(
    template: Template, profile: GithubProfile, avatar: Avatar, theme: Theme
) -> str:
    """Post: a self-contained SVG; the avatar is inlined because READMEs block external images."""
    rows = _rows(profile)
    agents = ", ".join(f"{row.name} {_format_tokens(row.tokens)}" for row in rows)
    description = f"{profile.login}: {_format_tokens(profile.total_tokens)} estimated tokens, {profile.rarity}"
    return template.render(
        name=_shortened_login(profile.login, _PROFILE_NAME_MAX_LENGTH),
        total_tokens=profile.total_tokens,
        rarity=profile.rarity,
        theme=theme,
        rows=rows,
        description=f"{description}. {agents}." if rows else f"{description}.",
        avatar_url=_avatar_data_url(avatar),
    )


def render_profile_card(profile: GithubProfile, avatar: Avatar, theme: Theme) -> str:
    """Post: the photo on top, then the name, rarity, total and agents."""
    return _render_profile_layout(_profile_template, profile, avatar, theme)


def render_wide_profile_card(profile: GithubProfile, avatar: Avatar, theme: Theme) -> str:
    """Post: the photo on the left, the name, rarity, total and agents on its right."""
    return _render_profile_layout(_wide_profile_template, profile, avatar, theme)


def render_scanning_card(login: str, theme: Theme) -> str:
    """Post: a placeholder shown while the first scan of a profile is still running."""
    return _render_notice(
        login, "Scanning public commits, back in a minute", is_pending=True, theme=theme
    )


def render_error_card(login: str, message: str, theme: Theme) -> str:
    """Post: a card explaining why the badge could not be drawn; READMEs show it instead of a broken image."""
    return _render_notice(login, message, is_pending=False, theme=theme)


def _render_notice(login: str, message: str, *, is_pending: bool, theme: Theme) -> str:
    return _notice_template.render(
        name=_shortened_login(login, _NOTICE_NAME_MAX_LENGTH),
        description=f"{login}: {message}",
        message=message,
        is_pending=is_pending,
        theme=theme,
    )
