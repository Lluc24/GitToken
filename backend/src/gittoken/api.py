import asyncio
import logging
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from typing import Annotated
from uuid import uuid4

import sentry_sdk
from fastapi import (
    BackgroundTasks,
    FastAPI,
    Header,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from loguru import logger
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    PositiveInt,
    SecretStr,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from sentry_sdk.integrations.loguru import LoguruIntegration

from gittoken.application import (
    fetch_fresh_leaderboard,
    fetch_profile_avatar,
    find_installation_login,
    finish_authorized_installation,
    lookup_profile,
    report_profile_search,
    today_utc,
    withdraw_consent,
)
from gittoken.badge import (
    Theme,
    render_badge,
    render_error_card,
    render_heatmap,
    render_profile_card,
    render_scanning_card,
)
from gittoken.db import SupabaseClient, create_supabase_client
from gittoken.domain import (
    GITHUB_LOGIN_PATTERN,
    MIN_TOKENS_BY_RARITY,
    NAME_BY_AGENT,
    Agent,
    GithubAuthorizationCode,
    GithubLoginKey,
    GithubProfile,
    GithubRequestError,
    InstallationAuthorization,
    InstallationId,
    InstallationNotFoundError,
    InvalidAuthorizationCodeError,
    InvalidWebhookError,
    OrganizationInstallationError,
    ProfileNotFoundError,
    ProfileStoreError,
    Rarity,
    VerifiedGithubUsername,
    login_key,
)
from gittoken.github import (
    GithubApiClient,
    GithubApp,
    GithubOauthClient,
    create_github_api_client,
    create_github_avatar_client,
    create_github_oauth_client,
    github_app_install_url,
    load_github_app_private_key,
    parse_webhook,
)
from gittoken.slack import SlackActivityClient, create_slack_activity_client
from gittoken.telemetry import configure_tracing

# Profiles are rescanned at most daily, so the CDN may keep these responses for a day.
_DAILY_CACHE_CONTROL = "public, max-age=0, s-maxage=86400, stale-while-revalidate=3600"
# GitHub's image proxy gives up after a few seconds, so a slower first scan answers with a placeholder.
_BADGE_LOOKUP_WAIT_SECONDS = 3
_SCANNING_CACHE_CONTROL = "public, max-age=0, s-maxage=60"
# Badge errors are drawn as a card with status 200, as a broken image explains nothing in a README.
_BADGE_ERROR_CACHE_CONTROL = "public, max-age=0, s-maxage=600"
_SLACK_WEBHOOK_URL_PREFIX = "https://hooks.slack.com/"


class ApiSettings(BaseSettings):
    # Validation errors would otherwise echo the raw settings, secrets included, into the logs.
    model_config = SettingsConfigDict(hide_input_in_errors=True, env_ignore_empty=True)

    github_token: SecretStr
    supabase_url: HttpUrl
    supabase_secret_key: SecretStr
    otel_exporter_otlp_endpoint: str = ""
    sentry_dsn: SecretStr = SecretStr("")
    github_app_id: PositiveInt
    github_app_private_key: SecretStr
    github_webhook_secret: SecretStr
    github_app_slug: str = Field(pattern="^[a-z0-9][a-z0-9-]*$")
    github_app_client_id: str = Field(min_length=1)
    github_app_client_secret: SecretStr
    slack_activity_webhook_url: SecretStr

    @property
    def github_app(self) -> GithubApp:
        return GithubApp(
            self.github_app_id,
            load_github_app_private_key(self.github_app_private_key),
            self.github_webhook_secret,
            self.github_app_slug,
            self.github_app_client_id,
            self.github_app_client_secret,
        )

    @field_validator("slack_activity_webhook_url")
    @classmethod
    def require_slack_webhook_url(cls, webhook_url: SecretStr) -> SecretStr:
        if not webhook_url.get_secret_value().startswith(_SLACK_WEBHOOK_URL_PREFIX):
            raise ValueError(
                f"SLACK_ACTIVITY_WEBHOOK_URL must start with {_SLACK_WEBHOOK_URL_PREFIX}"
            )
        return webhook_url


class ProfileTokensResponse(BaseModel):
    login: str
    total_tokens: int
    rarity: Rarity
    tokens_by_agent: dict[Agent, int]
    includes_private_repositories: bool
    install_url: str


class ProfileSearchEvent(BaseModel):
    login: Annotated[VerifiedGithubUsername, Field(pattern=GITHUB_LOGIN_PATTERN)]


class LeaderboardEntryResponse(BaseModel):
    login: str
    total_tokens: int
    rarity: Rarity


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
    with suppress(ProfileNotFoundError, GithubRequestError, ProfileStoreError):
        await lookup


class _ProfileLookups:
    """Invariant: at most one running lookup per login in any casing, so concurrent requests
    scan once."""

    def __init__(
        self,
        github_client: GithubApiClient,
        supabase_client: SupabaseClient,
        github_app: GithubApp,
    ) -> None:
        self._github_client = github_client
        self._supabase_client = supabase_client
        self._github_app = github_app
        self._running_lookup_by_login_key: dict[GithubLoginKey, asyncio.Task[GithubProfile]] = {}

    def start_or_join(self, login: VerifiedGithubUsername) -> asyncio.Task[GithubProfile]:
        key = login_key(login)
        if key not in self._running_lookup_by_login_key:
            self._running_lookup_by_login_key[key] = asyncio.create_task(
                lookup_profile(self._github_client, self._supabase_client, self._github_app, login)
            )
            self._running_lookup_by_login_key[key].add_done_callback(
                lambda _: self._running_lookup_by_login_key.pop(key)
            )
        return self._running_lookup_by_login_key[key]


async def _badge_response(
    login: VerifiedGithubUsername,
    theme: Theme,
    lookup: asyncio.Task[GithubProfile],
    background_tasks: BackgroundTasks,
    render_card: Callable[[GithubProfile], Awaitable[str]],
) -> Response:
    """Post: the card, an error card, or a scanning placeholder; always an SVG a README can show.
    A lookup still running after the badge wait is finished once the response is sent."""
    await asyncio.wait({lookup}, timeout=_BADGE_LOOKUP_WAIT_SECONDS)
    if lookup.done():
        try:
            svg = await render_card(lookup.result())
        except ProfileNotFoundError:
            return _badge_error_response(login, "No GitHub user with this name", theme)
        except GithubRequestError:
            return _badge_error_response(login, "GitHub is unavailable, retrying soon", theme)
        except ProfileStoreError:
            return _badge_error_response(login, "GitToken is unavailable, retrying soon", theme)
        return _svg_response(svg, _DAILY_CACHE_CONTROL)
    background_tasks.add_task(_finish_lookup, lookup)
    return _svg_response(render_scanning_card(login, theme), _SCANNING_CACHE_CONTROL)


def _add_github_app_routes(
    app: FastAPI,
    github_app: GithubApp,
    github_client: GithubApiClient,
    oauth_client: GithubOauthClient,
    supabase_client: SupabaseClient,
) -> None:
    @app.get("/v1/github-app/setup")
    async def finish_github_app_setup(
        installation_id: Annotated[InstallationId, Query(gt=0)],
        code: Annotated[GithubAuthorizationCode | None, Query(min_length=1)] = None,
    ) -> RedirectResponse:
        """GitHub sends the browser here after an install or a repository change, with code when
        the user authorized the app; without it nothing is changed."""
        no_store_headers = {"Cache-Control": "no-store"}
        try:
            login = (
                await finish_authorized_installation(
                    github_client,
                    oauth_client,
                    supabase_client,
                    github_app,
                    InstallationAuthorization(installation_id, code),
                )
                if code is not None
                else await find_installation_login(github_client, github_app, installation_id)
            )
        except InvalidAuthorizationCodeError as error:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, str(error), headers=no_store_headers
            ) from error
        except OrganizationInstallationError as error:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, str(error), headers=no_store_headers
            ) from error
        except InstallationNotFoundError as error:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, str(error), headers=no_store_headers
            ) from error
        except (GithubRequestError, ProfileStoreError) as error:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "GitHub App setup unavailable",
                headers=no_store_headers,
            ) from error
        # A fresh key for the profile page to pass on to its API requests, past the CDN's
        # copies from before the install.
        return RedirectResponse(
            f"/{login}?connected={uuid4().hex[:8]}",
            status.HTTP_303_SEE_OTHER,
            headers=no_store_headers,
        )

    @app.post("/v1/github-app/webhook", status_code=status.HTTP_204_NO_CONTENT)
    async def receive_github_webhook(
        request: Request,
        x_github_event: Annotated[str, Header()],
        x_hub_signature_256: Annotated[str, Header()],
    ) -> None:
        try:
            withdrawal = parse_webhook(
                github_app.webhook_secret,
                x_github_event,
                x_hub_signature_256,
                await request.body(),
            )
        except InvalidWebhookError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
        if withdrawal is not None:
            try:
                await withdraw_consent(supabase_client, withdrawal)
            except ProfileStoreError as error:
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    "Profiles covering withdrawn repositories could not be deleted",
                ) from error


def _add_profile_search_route(app: FastAPI, slack_client: SlackActivityClient) -> None:
    @app.post("/v1/events/profile-search", status_code=status.HTTP_202_ACCEPTED)
    async def receive_profile_search(event: ProfileSearchEvent) -> None:
        """The site sends this when a visitor submits a search. The Slack message is sent before
        answering, within its two-second timeout, as a serverless function may be frozen once it
        has answered; a failed send still answers 202."""
        await report_profile_search(slack_client, event.login)


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
    github_app = settings.github_app
    github_client = create_github_api_client(settings.github_token)
    avatar_client = create_github_avatar_client()
    oauth_client = create_github_oauth_client()
    supabase_client = create_supabase_client(settings.supabase_url, settings.supabase_secret_key)
    slack_client = create_slack_activity_client(settings.slack_activity_webhook_url)

    @asynccontextmanager
    async def close_clients_on_shutdown(_: FastAPI) -> AsyncIterator[None]:
        yield
        await github_client.aclose()
        await avatar_client.aclose()
        await oauth_client.aclose()
        await supabase_client.aclose()
        await slack_client.aclose()

    app = FastAPI(title="GitToken", lifespan=close_clients_on_shutdown)
    profile_lookups = _ProfileLookups(github_client, supabase_client, github_app)

    @app.get("/v1/users/{login}")
    async def get_user_tokens(
        login: Annotated[VerifiedGithubUsername, Path(pattern=GITHUB_LOGIN_PATTERN)],
        response: Response,
    ) -> ProfileTokensResponse:
        try:
            profile = await asyncio.shield(profile_lookups.start_or_join(login))
        except ProfileNotFoundError as error:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, str(error), headers={"Cache-Control": "no-store"}
            ) from error
        except (GithubRequestError, ProfileStoreError) as error:
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
            includes_private_repositories=profile.includes_private_repositories,
            install_url=github_app_install_url(github_app, profile.github_id),
        )

    _add_profile_search_route(app, slack_client)

    @app.get("/v1/badges/{login}.svg")
    async def get_badge(
        login: Annotated[VerifiedGithubUsername, Path(pattern=GITHUB_LOGIN_PATTERN)],
        background_tasks: BackgroundTasks,
        theme: Theme = Theme.DARK,
    ) -> Response:
        async def render_card(profile: GithubProfile) -> str:
            return render_badge(profile, theme)

        return await _badge_response(
            login,
            theme,
            profile_lookups.start_or_join(login),
            background_tasks,
            render_card,
        )

    @app.get("/v1/badges/{login}/profile.svg")
    async def get_profile_card(
        login: Annotated[VerifiedGithubUsername, Path(pattern=GITHUB_LOGIN_PATTERN)],
        background_tasks: BackgroundTasks,
        theme: Theme = Theme.DARK,
    ) -> Response:
        async def render_card(profile: GithubProfile) -> str:
            avatar = await fetch_profile_avatar(avatar_client, login)
            return render_profile_card(profile, avatar, theme)

        return await _badge_response(
            login,
            theme,
            profile_lookups.start_or_join(login),
            background_tasks,
            render_card,
        )

    @app.get("/v1/badges/{login}/activity.svg")
    async def get_activity_heatmap(
        login: Annotated[VerifiedGithubUsername, Path(pattern=GITHUB_LOGIN_PATTERN)],
        background_tasks: BackgroundTasks,
        theme: Theme = Theme.DARK,
    ) -> Response:
        async def render_card(profile: GithubProfile) -> str:
            return render_heatmap(profile, theme, today_utc())

        return await _badge_response(
            login,
            theme,
            profile_lookups.start_or_join(login),
            background_tasks,
            render_card,
        )

    @app.get("/v1/leaderboard")
    async def get_leaderboard(response: Response) -> list[LeaderboardEntryResponse]:
        try:
            entries = await fetch_fresh_leaderboard(supabase_client)
        except ProfileStoreError as error:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "Leaderboard unavailable",
                headers={"Cache-Control": "no-store"},
            ) from error

        response.headers["Cache-Control"] = (
            "public, max-age=0, s-maxage=60, stale-while-revalidate=300"
        )
        return [
            LeaderboardEntryResponse(
                login=entry.login, total_tokens=entry.total_tokens, rarity=entry.rarity
            )
            for entry in entries
        ]

    _add_github_app_routes(app, github_app, github_client, oauth_client, supabase_client)

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
