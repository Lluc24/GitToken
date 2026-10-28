import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable, Coroutine
from functools import partial
from typing import Annotated

import httpx
import sentry_sdk
from fastapi import BackgroundTasks, FastAPI, HTTPException, Path, Response, status
from loguru import logger
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings
from sentry_sdk.integrations.loguru import LoguruIntegration

from gittoken.application import fetch_fresh_leaderboard, lookup_profile
from gittoken.badge import (
    Theme,
    render_badge,
    render_error_card,
    render_profile_card,
    render_scanning_card,
)
from gittoken.db import LeaderboardEntry
from gittoken.domain import (
    MIN_TOKENS_BY_RARITY,
    NAME_BY_AGENT,
    Agent,
    GithubProfile,
    GithubRequestError,
    ProfileNotFoundError,
    Rarity,
    VerifiedGithubUsername,
)
from gittoken.github import fetch_avatar
from gittoken.telemetry import configure_tracing

_GITHUB_LOGIN_PATTERN = "^[A-Za-z0-9][A-Za-z0-9-]{0,38}$"
# Profiles are rescanned at most daily, so the CDN may keep these responses for a day.
_DAILY_CACHE_CONTROL = "public, max-age=0, s-maxage=86400, stale-while-revalidate=3600"
# GitHub's image proxy gives up after a few seconds, so a slower first scan answers with a placeholder.
_BADGE_LOOKUP_WAIT_SECONDS = 3
_SCANNING_CACHE_CONTROL = "public, max-age=0, s-maxage=60"
# Badge errors are drawn as a card with status 200, as a broken image explains nothing in a README.
_BADGE_ERROR_CACHE_CONTROL = "public, max-age=0, s-maxage=600"


class ApiSettings(BaseSettings):
    github_token: SecretStr
    supabase_url: str
    supabase_secret_key: SecretStr
    otel_exporter_otlp_endpoint: str = ""
    sentry_dsn: SecretStr = SecretStr("")


class ProfileTokensResponse(BaseModel):
    login: str
    total_tokens: int
    rarity: Rarity
    tokens_by_agent: dict[Agent, int]


class AgentResponse(BaseModel):
    agent: Agent
    name: str


class RarityResponse(BaseModel):
    rarity: Rarity
    min_tokens: int


def _svg_response(svg: str, cache_control: str) -> Response:
    return Response(
        svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": cache_control, "X-Content-Type-Options": "nosniff"},
    )


def _badge_error_response(login: str, message: str, theme: Theme) -> Response:
    return _svg_response(render_error_card(login, message, theme), _BADGE_ERROR_CACHE_CONTROL)


async def _finish_lookup(lookup: asyncio.Task[GithubProfile]) -> None:
    await lookup


# Badge requests for the same login share one lookup, so a page showing two badges scans once.
_badge_lookups: dict[str, asyncio.Task[GithubProfile]] = {}


async def _lookup_within_badge_wait(
    login: str,
    lookup_profile: Callable[[], Coroutine[object, object, GithubProfile]],
    background_tasks: BackgroundTasks,
) -> asyncio.Task[GithubProfile]:
    """Post: a finished lookup, or one that keeps running after the response is sent."""
    if login not in _badge_lookups:
        _badge_lookups[login] = asyncio.create_task(lookup_profile())
        _badge_lookups[login].add_done_callback(lambda _: _badge_lookups.pop(login))
    lookup = _badge_lookups[login]
    await asyncio.wait({lookup}, timeout=_BADGE_LOOKUP_WAIT_SECONDS)
    if not lookup.done():
        background_tasks.add_task(_finish_lookup, lookup)
    return lookup


async def _badge_response(
    login: VerifiedGithubUsername,
    theme: Theme,
    lookup_profile: Callable[[], Coroutine[object, object, GithubProfile]],
    background_tasks: BackgroundTasks,
    render_card: Callable[[GithubProfile], Awaitable[str]],
) -> Response:
    """Post: the card, an error card, or a scanning placeholder; always an SVG a README can show."""
    lookup = await _lookup_within_badge_wait(login, lookup_profile, background_tasks)
    if lookup.done():
        try:
            svg = await render_card(lookup.result())
        except ProfileNotFoundError:
            return _badge_error_response(login, "No GitHub user with this name", theme)
        except (httpx.HTTPError, GithubRequestError):
            return _badge_error_response(login, "GitHub is unavailable, retrying soon", theme)
        return _svg_response(svg, _DAILY_CACHE_CONTROL)
    return _svg_response(render_scanning_card(login, theme), _SCANNING_CACHE_CONTROL)


def create_app() -> FastAPI:
    settings = ApiSettings()
    logger.remove()
    logger.add(sys.stderr, serialize=True, diagnose=False, backtrace=False)
    if settings.sentry_dsn.get_secret_value():
        sentry_sdk.init(
            dsn=settings.sentry_dsn.get_secret_value(),
            default_integrations=False,
            integrations=[
                LoguruIntegration(
                    level=None,
                    event_level=logging.WARNING,
                    sentry_logs_level=None,
                    capture_sentry_logs=False,
                )
            ],
            send_default_pii=False,
            include_local_variables=False,
            traces_sample_rate=0,
        )
    configure_tracing(settings.otel_exporter_otlp_endpoint)
    app = FastAPI(title="GitToken")
    lookup_settings_profile = partial(
        lookup_profile,
        settings.github_token.get_secret_value(),
        settings.supabase_url,
        settings.supabase_secret_key.get_secret_value(),
    )

    @app.get("/v1/users/{login}")
    async def get_user_tokens(
        login: Annotated[VerifiedGithubUsername, Path(pattern=_GITHUB_LOGIN_PATTERN)],
        response: Response,
    ) -> ProfileTokensResponse:
        try:
            profile = await lookup_settings_profile(login)
        except ProfileNotFoundError as error:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, str(error), headers={"Cache-Control": "no-store"}
            ) from error
        except (httpx.HTTPError, GithubRequestError) as error:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "Profile lookup unavailable",
                headers={"Cache-Control": "no-store"},
            ) from error
        response.headers["Cache-Control"] = _DAILY_CACHE_CONTROL
        return ProfileTokensResponse(
            login=profile.login,
            total_tokens=profile.total_tokens,
            rarity=profile.rarity,
            tokens_by_agent=profile.tokens_by_agent,
        )

    @app.get("/v1/badges/{login}.svg")
    async def get_badge(
        login: Annotated[VerifiedGithubUsername, Path(pattern=_GITHUB_LOGIN_PATTERN)],
        background_tasks: BackgroundTasks,
        theme: Theme = Theme.DARK,
    ) -> Response:
        async def render_card(profile: GithubProfile) -> str:
            return render_badge(profile, theme)

        return await _badge_response(
            login,
            theme,
            lambda: lookup_settings_profile(login),
            background_tasks,
            render_card,
        )

    @app.get("/v1/badges/{login}/profile.svg")
    async def get_profile_card(
        login: Annotated[VerifiedGithubUsername, Path(pattern=_GITHUB_LOGIN_PATTERN)],
        background_tasks: BackgroundTasks,
        theme: Theme = Theme.DARK,
    ) -> Response:
        async def render_card(profile: GithubProfile) -> str:
            avatar = await fetch_avatar(login)
            return render_profile_card(profile, avatar, theme)

        return await _badge_response(
            login,
            theme,
            lambda: lookup_settings_profile(login),
            background_tasks,
            render_card,
        )

    @app.get("/v1/leaderboard")
    async def get_leaderboard(response: Response) -> list[LeaderboardEntry]:
        try:
            entries = await fetch_fresh_leaderboard(
                settings.supabase_url, settings.supabase_secret_key.get_secret_value()
            )
        except httpx.HTTPError as error:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "Leaderboard unavailable",
                headers={"Cache-Control": "no-store"},
            ) from error

        response.headers["Cache-Control"] = (
            "public, max-age=0, s-maxage=60, stale-while-revalidate=300"
        )
        return entries

    @app.get("/v1/agents")
    def get_agents() -> list[AgentResponse]:
        return [AgentResponse(agent=agent, name=name) for agent, name in NAME_BY_AGENT.items()]

    @app.get("/v1/rarities")
    def get_rarities() -> list[RarityResponse]:
        """Post: lowest rarity first."""
        return [
            RarityResponse(rarity=rarity, min_tokens=min_tokens)
            for rarity, min_tokens in MIN_TOKENS_BY_RARITY.items()
        ]

    app.frontend("/", directory="frontend/dist")
    return app


app = create_app()
