from collections.abc import Awaitable, Callable
from typing import Annotated

import httpx
from fastapi import FastAPI, Path, Request, status
from fastapi.responses import JSONResponse
from pydantic import SecretStr
from pydantic_settings import BaseSettings

from gittoken.domain.github_profile import ProfileNotFoundError, VerifiedGithubUsername
from gittoken.entrypoints.api.schemas import ProfileTokensResponse
from gittoken.integrations.github_graphql import fetch_github_profile

_GITHUB_LOGIN_PATTERN = "^[A-Za-z0-9][A-Za-z0-9-]{0,38}$"


class ApiSettings(BaseSettings):
    github_token: SecretStr


def _error_handler(status_code: int) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handle(_: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(error)})

    return handle


def create_app() -> FastAPI:
    settings = ApiSettings()
    app = FastAPI(title="GitToken")

    @app.get("/v1/users/{login}")
    async def get_user_tokens(
        login: Annotated[VerifiedGithubUsername, Path(pattern=_GITHUB_LOGIN_PATTERN)],
    ) -> ProfileTokensResponse:
        profile = await fetch_github_profile(settings.github_token.get_secret_value(), login)
        return ProfileTokensResponse(
            login=profile.login, total_tokens=profile.total_tokens, tokens_by_agent=profile.tokens_by_agent
        )

    app.add_exception_handler(ProfileNotFoundError, _error_handler(status.HTTP_404_NOT_FOUND))
    app.add_exception_handler(httpx.HTTPError, _error_handler(status.HTTP_502_BAD_GATEWAY))
    return app
