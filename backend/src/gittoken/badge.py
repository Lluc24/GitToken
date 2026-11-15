from base64 import b64encode
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from io import BytesIO

from jinja2 import Environment, PackageLoader, StrictUndefined
from PIL import Image

from gittoken.domain import NAME_BY_AGENT, Avatar, GithubProfile

_MAX_ROWS = 2
_AVATAR_JPEG_QUALITY = 82
_HEATMAP_WEEKS = 53
_DAYS_PER_WEEK = 7
# The last weeks leave no room for a month name before the card's edge.
_HEATMAP_LAST_LABELLED_WEEK = _HEATMAP_WEEKS - 3


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
        total_tokens=profile.total_tokens,
        rarity=profile.rarity,
        theme=theme,
        rows=_rows(profile),
    )


@dataclass(frozen=True)
class _HeatmapCell:
    week: int
    weekday: int
    level: int


@dataclass(frozen=True)
class _MonthLabel:
    week: int
    name: str


def _activity_level(tokens: int, quartile_tokens: tuple[int, ...]) -> int:
    """Pre: quartile_tokens are the quartiles of the window's non-zero daily tokens.
    Post: 0 for a day without agent commits, else 1 to 4 by quartile, as GitHub shades its graph."""
    level = 0
    if tokens:
        level = 1 + sum(tokens > quartile for quartile in quartile_tokens)
    return level


def _quartile_tokens(daily_tokens: list[int]) -> tuple[int, ...]:
    """Post: the first, second and third quartiles of the non-zero daily_tokens; empty if none."""
    active_tokens = sorted(tokens for tokens in daily_tokens if tokens)
    quartiles: tuple[int, ...] = ()
    if active_tokens:
        quartiles = tuple(active_tokens[len(active_tokens) * quarter // 4] for quarter in (1, 2, 3))
    return quartiles


def render_heatmap(profile: GithubProfile, theme: Theme, today: date) -> str:
    """Post: a grid of the 53 weeks up to today, Sunday first, each day shaded by its tokens."""
    first_day = today - timedelta(
        days=(today.weekday() + 1) % _DAYS_PER_WEEK + _DAYS_PER_WEEK * (_HEATMAP_WEEKS - 1)
    )
    days = [first_day + timedelta(days=offset) for offset in range((today - first_day).days + 1)]
    activity_by_day = profile.activity_by_day
    active_days = [activity_by_day[day] for day in days if day in activity_by_day]
    daily_tokens = [activity_by_day[day].tokens if day in activity_by_day else 0 for day in days]
    quartile_tokens = _quartile_tokens(daily_tokens)
    cells = [
        _HeatmapCell(
            offset // _DAYS_PER_WEEK,
            offset % _DAYS_PER_WEEK,
            _activity_level(tokens, quartile_tokens),
        )
        for offset, tokens in enumerate(daily_tokens)
    ]
    month_labels = [
        _MonthLabel(offset // _DAYS_PER_WEEK, day.strftime("%b"))
        for offset, day in enumerate(days)
        if offset % _DAYS_PER_WEEK == 0
        and day.day <= _DAYS_PER_WEEK
        and offset // _DAYS_PER_WEEK <= _HEATMAP_LAST_LABELLED_WEEK
    ]
    return _heatmap_template.render(
        login=profile.login,
        theme=theme,
        weeks=_HEATMAP_WEEKS,
        cells=cells,
        month_labels=month_labels,
        total_tokens=sum(daily_tokens),
        total_commits=sum(activity.commits for activity in active_days),
    )


def _avatar_data_url(avatar: Avatar) -> str:
    """Post: a JPEG data URL; GitHub serves some photos as PNGs several times larger."""
    jpeg = BytesIO()
    with Image.open(BytesIO(avatar)) as image:
        image.convert("RGB").save(jpeg, "JPEG", quality=_AVATAR_JPEG_QUALITY, optimize=True)
    return f"data:image/jpeg;base64,{b64encode(jpeg.getvalue()).decode()}"


def render_profile_card(profile: GithubProfile, avatar: Avatar, theme: Theme) -> str:
    """Post: a self-contained SVG; the avatar is inlined because READMEs block external images."""
    rows = _rows(profile)
    agents = ", ".join(f"{row.name} {_format_tokens(row.tokens)}" for row in rows)
    description = f"{profile.login}: {_format_tokens(profile.total_tokens)} estimated tokens, {profile.rarity}"
    return _profile_template.render(
        login=profile.login,
        total_tokens=profile.total_tokens,
        rarity=profile.rarity,
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
