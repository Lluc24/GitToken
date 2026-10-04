from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, Path, status
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings

from gittoken.domain import Agent, ProfileNotFoundError, VerifiedGithubUsername
from gittoken.github import fetch_github_profile

_GITHUB_LOGIN_PATTERN = "^[A-Za-z0-9][A-Za-z0-9-]{0,38}$"


class ApiSettings(BaseSettings):
    github_token: SecretStr


class ProfileTokensResponse(BaseModel):
    login: str
    total_tokens: int
    tokens_by_agent: dict[Agent, int]


def create_app() -> FastAPI:
    settings = ApiSettings()
    app = FastAPI(title="GitToken")

    @app.get("/v1/users/{login}")
    async def get_user_tokens(
        login: Annotated[VerifiedGithubUsername, Path(pattern=_GITHUB_LOGIN_PATTERN)],
    ) -> ProfileTokensResponse:
        try:
            profile = await fetch_github_profile(settings.github_token.get_secret_value(), login)
        except ProfileNotFoundError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
        except httpx.HTTPError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
        return ProfileTokensResponse(
            login=profile.login,
            total_tokens=profile.total_tokens,
            tokens_by_agent=profile.tokens_by_agent,
        )

    app.frontend("/", directory="frontend/dist")
    return app


app = create_app()
