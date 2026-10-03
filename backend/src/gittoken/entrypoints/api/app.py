from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, SecretStr
from pydantic_settings import BaseSettings

from gittoken.application.estimate_profile_tokens import EstimateProfileTokens
from gittoken.application.ports import ProfileNotFoundError
from gittoken.domain.github_login import GithubLogin, InvalidGithubLoginError
from gittoken.entrypoints.api.schemas import ErrorResponse, ProfileTokensResponse, profile_tokens_response
from gittoken.entrypoints.api.signatures_file import load_agent_signatures
from gittoken.integrations.github_graphql import GithubApiError, GithubGraphqlClient

_GITHUB_TIMEOUT_SECONDS = 30


class ApiSettings(BaseSettings):
    github_token: SecretStr
    agent_signatures_file: Path = Path("data/signatures.yaml")
    commits_since: AwareDatetime = datetime(2025, 1, 1, tzinfo=UTC)
    maximum_concurrent_github_requests: int = 8


def _v1_router(estimate_profile_tokens: EstimateProfileTokens) -> APIRouter:
    router = APIRouter(prefix="/v1")

    @router.get(
        "/users/{login}",
        responses={
            status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
            status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
            status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
        },
    )
    async def get_user_tokens(login: str) -> ProfileTokensResponse:
        return profile_tokens_response(await estimate_profile_tokens.execute(GithubLogin(login)))

    return router


def _error_handler(status_code: int) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handle(_: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content=ErrorResponse(detail=str(error)).model_dump())

    return handle


def create_app() -> FastAPI:
    settings = ApiSettings()
    http_client = httpx.AsyncClient(timeout=_GITHUB_TIMEOUT_SECONDS)
    estimate_profile_tokens = EstimateProfileTokens(
        github=GithubGraphqlClient(
            http_client,
            settings.github_token.get_secret_value(),
            settings.maximum_concurrent_github_requests,
        ),
        signatures=load_agent_signatures(settings.agent_signatures_file),
        commits_since=settings.commits_since,
    )

    @asynccontextmanager
    async def close_http_client_on_shutdown(_: FastAPI) -> AsyncIterator[None]:
        yield
        await http_client.aclose()

    app = FastAPI(title="GitToken", lifespan=close_http_client_on_shutdown)
    app.include_router(_v1_router(estimate_profile_tokens))
    app.add_exception_handler(InvalidGithubLoginError, _error_handler(status.HTTP_400_BAD_REQUEST))
    app.add_exception_handler(ProfileNotFoundError, _error_handler(status.HTTP_404_NOT_FOUND))
    app.add_exception_handler(GithubApiError, _error_handler(status.HTTP_502_BAD_GATEWAY))
    app.add_exception_handler(httpx.HTTPError, _error_handler(status.HTTP_502_BAD_GATEWAY))
    return app
