from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, Path, status
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings

from gittoken.db import fetch_cached_profile, save_profile
from gittoken.domain import (
    MIN_TOKENS_BY_RARITY,
    Agent,
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
    app = FastAPI(title="GitToken")

    @app.get("/v1/users/{login}")
    async def get_user_tokens(
        login: Annotated[VerifiedGithubUsername, Path(pattern=_GITHUB_LOGIN_PATTERN)],
    ) -> ProfileTokensResponse:
        supabase_secret_key = settings.supabase_secret_key.get_secret_value()
        try:
            profile = await fetch_cached_profile(settings.supabase_url, supabase_secret_key, login)
            if profile is None:
                profile = await fetch_github_profile(
                    settings.github_token.get_secret_value(), login
                )
                await save_profile(settings.supabase_url, supabase_secret_key, profile)
        except ProfileNotFoundError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
        except httpx.HTTPError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
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
