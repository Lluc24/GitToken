import logging
import sys
from time import perf_counter
from typing import Annotated

import httpx
import sentry_sdk
from fastapi import FastAPI, HTTPException, Path, status
from loguru import logger
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings
from sentry_sdk.integrations.loguru import LoguruIntegration

from gittoken.db import fetch_cached_profile, save_profile
from gittoken.domain import (
    MIN_TOKENS_BY_RARITY,
    Agent,
    GithubRequestError,
    ProfileNotFoundError,
    Rarity,
    VerifiedGithubUsername,
)
from gittoken.github import fetch_github_profile

_GITHUB_LOGIN_PATTERN = "^[A-Za-z0-9][A-Za-z0-9-]{0,38}$"


class ApiSettings(BaseSettings):
    github_token: SecretStr
    supabase_url: str
    supabase_secret_key: SecretStr
    sentry_dsn: SecretStr = SecretStr("")


class ProfileTokensResponse(BaseModel):
    login: str
    total_tokens: int
    rarity: Rarity
    tokens_by_agent: dict[Agent, int]


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
    app = FastAPI(title="GitToken")

    @app.get("/v1/users/{login}")
    async def get_user_tokens(
        login: Annotated[VerifiedGithubUsername, Path(pattern=_GITHUB_LOGIN_PATTERN)],
    ) -> ProfileTokensResponse:
        started_at = perf_counter()
        supabase_secret_key = settings.supabase_secret_key.get_secret_value()
        try:
            profile = await fetch_cached_profile(settings.supabase_url, supabase_secret_key, login)
            cache_hit = profile is not None
            if profile is None:
                profile = await fetch_github_profile(
                    settings.github_token.get_secret_value(), login
                )
                await save_profile(settings.supabase_url, supabase_secret_key, profile)
        except ProfileNotFoundError as error:
            logger.bind(
                event="profile_not_found", duration_seconds=perf_counter() - started_at
            ).info("Profile lookup returned no user")
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
        except (httpx.HTTPError, GithubRequestError) as error:
            logger.bind(
                event="profile_upstream_error",
                error_type=type(error).__name__,
                duration_seconds=perf_counter() - started_at,
            ).warning("Profile lookup failed")
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, "Profile lookup unavailable"
            ) from error
        logger.bind(
            event="profile_lookup",
            cache_hit=cache_hit,
            duration_seconds=perf_counter() - started_at,
        ).info("Profile lookup completed")
        return ProfileTokensResponse(
            login=profile.login,
            total_tokens=profile.total_tokens,
            rarity=profile.rarity,
            tokens_by_agent=profile.tokens_by_agent,
        )

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
