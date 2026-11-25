from base64 import b64encode
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from io import BytesIO

from jinja2 import Environment, PackageLoader, StrictUndefined
from PIL import Image

from gittoken.domain import NAME_BY_AGENT, Avatar, DayActivity, GithubProfile

_MAX_ROWS = 2
_PROFILE_NAME_MAX_LENGTH = 20
_HEATMAP_NAME_MAX_LENGTH = 24
_NOTICE_NAME_MAX_LENGTH = 20
_AVATAR_JPEG_QUALITY = 82
_HEATMAP_WEEKS = 53
_DAYS_PER_WEEK = 7
_NO_ACTIVITY = DayActivity(0, 0)


class Theme(StrEnum):
    DARK = "dark"
    LIGHT = "light"


@dataclass(frozen=True)
class AgentRow:
    mark: str
    name: str
    tokens: int
    share: float
    percent: int


def _format_tokens(tokens: int) -> str:
    for threshold, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if tokens >= threshold:
            whole, tenth = divmod((tokens * 10 + threshold // 2) // threshold, 10)
            return f"{whole}{suffix}" if tenth == 0 else f"{whole}.{tenth}{suffix}"
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
_badge_template = _environment.get_template("badge.svg.jinja")
_profile_template = _environment.get_template("profile.svg.jinja")
_notice_template = _environment.get_template("notice.svg.jinja")
_heatmap_template = _environment.get_template("heatmap.svg.jinja")


def _row(mark: str, name: str, tokens: int, total_tokens: int) -> AgentRow:
    share = tokens / total_tokens if total_tokens else 0
    return AgentRow(mark=mark, name=name, tokens=tokens, share=share, percent=round(share * 100))


def agent_rows(profile: GithubProfile) -> list[AgentRow]:
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
        rows=agent_rows(profile),
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


def _activity_level(activity: DayActivity, quartile_tokens: tuple[int, ...]) -> int:
    """Pre: quartile_tokens are the quartiles of the window's tokens on days with agent commits.
    Post: 0 for a day without agent commits, else 1 to 4 by quartile, as GitHub shades its graph."""
    level = 0
    if activity.commits:
        level = 1 + sum(activity.tokens > quartile for quartile in quartile_tokens)
    return level


def _quartile_tokens(daily_activities: list[DayActivity]) -> tuple[int, ...]:
    """Post: the first, second and third quartiles of tokens on days with agent commits; empty
    if there are none."""
    active_tokens = sorted(activity.tokens for activity in daily_activities if activity.commits)
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
    daily_activities = [activity_by_day.get(day, _NO_ACTIVITY) for day in days]
    quartile_tokens = _quartile_tokens(daily_activities)
    cells = [
        _HeatmapCell(
            offset // _DAYS_PER_WEEK,
            offset % _DAYS_PER_WEEK,
            _activity_level(activity, quartile_tokens),
        )
        for offset, activity in enumerate(daily_activities)
    ]
    month_labels = [
        _MonthLabel(offset // _DAYS_PER_WEEK, day.strftime("%b"))
        for offset, day in enumerate(days)
        if offset % _DAYS_PER_WEEK == 0 and day.day <= _DAYS_PER_WEEK
    ]
    total_tokens = sum(activity.tokens for activity in daily_activities)
    commits_text = f"{sum(activity.commits for activity in daily_activities):,} agent commits"
    return _heatmap_template.render(
        name=_shortened_login(profile.login, _HEATMAP_NAME_MAX_LENGTH),
        description=f"{profile.login}: {total_tokens:,} estimated tokens in {commits_text} over the last year",
        caption=f"tokens across {commits_text} in the last year",
        theme=theme,
        weeks=_HEATMAP_WEEKS,
        days_per_week=_DAYS_PER_WEEK,
        cells=cells,
        month_labels=month_labels,
        total_tokens=total_tokens,
    )


def _avatar_data_url(avatar: Avatar) -> str:
    """Post: a JPEG data URL; GitHub serves some photos as PNGs several times larger."""
    jpeg = BytesIO()
    with Image.open(BytesIO(avatar)) as image:
        image.convert("RGB").save(jpeg, "JPEG", quality=_AVATAR_JPEG_QUALITY, optimize=True)
    return f"data:image/jpeg;base64,{b64encode(jpeg.getvalue()).decode()}"


def render_profile_card(profile: GithubProfile, avatar: Avatar, theme: Theme) -> str:
    """Post: a self-contained SVG; the avatar is inlined because READMEs block external images."""
    rows = agent_rows(profile)
    agents = ", ".join(f"{row.name} {_format_tokens(row.tokens)}" for row in rows)
    description = f"{profile.login}: {_format_tokens(profile.total_tokens)} estimated tokens, {profile.rarity}"
    return _profile_template.render(
        name=_shortened_login(profile.login, _PROFILE_NAME_MAX_LENGTH),
        total_tokens=profile.total_tokens,
        rarity=profile.rarity,
        theme=theme,
        rows=rows,
        description=f"{description}. {agents}." if rows else f"{description}.",
        avatar_url=_avatar_data_url(avatar),
    )


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
