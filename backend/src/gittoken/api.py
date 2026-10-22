import logging
import sys
from time import perf_counter
from typing import Annotated

import httpx
import sentry_sdk
from fastapi import FastAPI, HTTPException, Path, Response, status
from loguru import logger
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings
from sentry_sdk.integrations.loguru import LoguruIntegration

from gittoken.badge import render_badge
from gittoken.db import LeaderboardEntry, fetch_cached_profile, fetch_leaderboard, save_profile
from gittoken.domain import (
    MIN_TOKENS_BY_RARITY,
    NAME_BY_AGENT,
    Agent,
    GithubRequestError,
    ProfileNotFoundError,
    Rarity,
    VerifiedGithubUsername,
)
from gittoken.github import fetch_avatar_data_url, fetch_github_profile
from gittoken.telemetry import configure_tracing, tracer

_GITHUB_LOGIN_PATTERN = "^[A-Za-z0-9][A-Za-z0-9-]{0,38}$"


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

    @app.get("/v1/users/{login}")
    async def get_user_tokens(
        login: Annotated[VerifiedGithubUsername, Path(pattern=_GITHUB_LOGIN_PATTERN)],
        response: Response,
    ) -> ProfileTokensResponse:
        started_at = perf_counter()
        supabase_secret_key = settings.supabase_secret_key.get_secret_value()
        try:
            with tracer.start_as_current_span(
                "cache.supabase.read", record_exception=False, set_status_on_exception=False
            ):
                profile = await fetch_cached_profile(
                    settings.supabase_url, supabase_secret_key, login
                )
            cache_hit = profile is not None
            if profile is None:
                with tracer.start_as_current_span(
                    "github.scan", record_exception=False, set_status_on_exception=False
                ):
                    profile = await fetch_github_profile(
                        settings.github_token.get_secret_value(), login
                    )
                with tracer.start_as_current_span(
                    "profile.persist", record_exception=False, set_status_on_exception=False
                ):
                    await save_profile(settings.supabase_url, supabase_secret_key, profile)
        except ProfileNotFoundError as error:
            logger.bind(
                event="profile_not_found", duration_seconds=perf_counter() - started_at
            ).info("Profile lookup returned no user")
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, str(error), headers={"Cache-Control": "no-store"}
            ) from error
        except (httpx.HTTPError, GithubRequestError) as error:
            logger.bind(
                event="profile_upstream_error",
                error_type=type(error).__name__,
                duration_seconds=perf_counter() - started_at,
            ).warning("Profile lookup failed")
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "Profile lookup unavailable",
                headers={"Cache-Control": "no-store"},
            ) from error
        logger.bind(
            event="profile_lookup",
            cache_hit=cache_hit,
            duration_seconds=perf_counter() - started_at,
        ).info("Profile lookup completed")
        response.headers["Cache-Control"] = (
            "public, max-age=0, s-maxage=3600, stale-while-revalidate=3600"
        )
        return ProfileTokensResponse(
            login=profile.login,
            total_tokens=profile.total_tokens,
            rarity=profile.rarity,
            tokens_by_agent=profile.tokens_by_agent,
        )

    @app.get("/v1/badges/{login}.svg")
    async def get_badge(
        login: Annotated[VerifiedGithubUsername, Path(pattern=_GITHUB_LOGIN_PATTERN)],
    ) -> Response:
        profile = await get_user_tokens(login, Response())
        try:
            avatar_data_url = await fetch_avatar_data_url(login)
        except (httpx.HTTPError, GithubRequestError) as error:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "Avatar unavailable",
                headers={"Cache-Control": "no-store"},
            ) from error
        return Response(
            render_badge(
                profile.login,
                profile.total_tokens,
                profile.tokens_by_agent,
                profile.rarity,
                avatar_data_url,
            ),
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "public, max-age=0, s-maxage=3600, stale-while-revalidate=3600",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.get("/v1/leaderboard")
    async def get_leaderboard(response: Response) -> list[LeaderboardEntry]:
        try:
            entries = await fetch_leaderboard(
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
