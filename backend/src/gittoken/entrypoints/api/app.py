from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import FastAPI, Path, Request, status
from fastapi.responses import JSONResponse
from pydantic import SecretStr
from pydantic_settings import BaseSettings

from gittoken.application.estimate_profile_tokens import EstimateProfileTokens
from gittoken.application.ports import ProfileNotFoundError
from gittoken.entrypoints.api.schemas import ProfileTokensResponse
from gittoken.integrations.github_graphql import GithubApiError, GithubGraphqlClient

_GITHUB_TIMEOUT_SECONDS = 30
_MAXIMUM_CONCURRENT_GITHUB_REQUESTS = 8
_COMMITS_SINCE = datetime(2025, 1, 1, tzinfo=UTC)
_GITHUB_LOGIN_PATTERN = "^[A-Za-z0-9][A-Za-z0-9-]{0,38}$"


class ApiSettings(BaseSettings):
    github_token: SecretStr


def _error_handler(status_code: int) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handle(_: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(error)})

    return handle


def create_app() -> FastAPI:
    settings = ApiSettings()
    http_client = httpx.AsyncClient(timeout=_GITHUB_TIMEOUT_SECONDS)
    estimate_profile_tokens = EstimateProfileTokens(
        github=GithubGraphqlClient(
            http_client, settings.github_token.get_secret_value(), _MAXIMUM_CONCURRENT_GITHUB_REQUESTS
        ),
        commits_since=_COMMITS_SINCE,
    )

    @asynccontextmanager
    async def close_http_client_on_shutdown(_: FastAPI) -> AsyncIterator[None]:
        yield
        await http_client.aclose()

    app = FastAPI(title="GitToken", lifespan=close_http_client_on_shutdown)

    @app.get("/v1/users/{login}")
    async def get_user_tokens(login: Annotated[str, Path(pattern=_GITHUB_LOGIN_PATTERN)]) -> ProfileTokensResponse:
        profile = await estimate_profile_tokens.execute(login)
        return ProfileTokensResponse(
            login=profile.login, total_tokens=profile.total_tokens, tokens_by_agent=profile.tokens_by_agent
        )

    app.add_exception_handler(ProfileNotFoundError, _error_handler(status.HTTP_404_NOT_FOUND))
    app.add_exception_handler(GithubApiError, _error_handler(status.HTTP_502_BAD_GATEWAY))
    app.add_exception_handler(httpx.HTTPError, _error_handler(status.HTTP_502_BAD_GATEWAY))
    return app
