import asyncio
import hmac
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from types import MappingProxyType
from typing import Literal, NewType, Self

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    SecretStr,
    TypeAdapter,
    ValidationError,
    model_validator,
)

from gittoken.domain import (
    GITHUB_LOGIN_PATTERN,
    AccountDisconnected,
    Agent,
    Avatar,
    ConsentWithdrawal,
    GithubAuthorizationCode,
    GithubProfile,
    GithubRequestError,
    GithubUserId,
    InstallationId,
    InstallationNotFoundError,
    InvalidAuthorizationCodeError,
    InvalidWebhookError,
    OrganizationInstallationError,
    PersonalInstallation,
    PrivateRepository,
    ProfileNotFoundError,
    RepositoriesRevoked,
    RepositoryId,
    VerifiedGithubUsername,
    find_agent,
)

_API_URL = "https://api.github.com"
_AVATAR_URL = "https://avatars.githubusercontent.com"
_OAUTH_URL = "https://github.com"
# Twice the 276-pixel photo on the profile card, for high-density screens.
_AVATAR_SIZE_PIXELS = 552
_AVATAR_MEDIA_TYPES = frozenset({"image/png", "image/jpeg", "image/gif"})
_TIMEOUT_SECONDS = 30
_MAXIMUM_CONCURRENT_REPOSITORIES = 8
_COMMITS_SINCE = datetime(2025, 1, 1, tzinfo=UTC)
# GitHub rejects app tokens that expire more than 10 minutes ahead; a minute back absorbs clock drift.
_APP_TOKEN_ISSUED_EARLIER = timedelta(minutes=1)
_APP_TOKEN_LIFETIME = timedelta(minutes=9)
_REST_HEADERS = MappingProxyType(
    {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
)
_REPOSITORIES_PER_PAGE = 100

GithubApiClient = NewType("GithubApiClient", httpx.AsyncClient)

# A client for GitHub's OAuth host; a separate client so the API token never reaches it.
GithubOauthClient = NewType("GithubOauthClient", httpx.AsyncClient)

# A client for GitHub's avatar host; a separate client so the API token never reaches it.
GithubAvatarClient = NewType("GithubAvatarClient", httpx.AsyncClient)


@dataclass(frozen=True)
class GithubApp:
    id: int
    private_key: RSAPrivateKey
    webhook_secret: SecretStr
    slug: str
    client_id: str
    client_secret: SecretStr


def load_github_app_private_key(private_key_pem: SecretStr) -> RSAPrivateKey:
    """Post: the RSA key, or ValueError naming what the PEM holds instead."""
    private_key = load_pem_private_key(private_key_pem.get_secret_value().encode(), password=None)
    if isinstance(private_key, RSAPrivateKey):
        return private_key
    raise ValueError(f"GITHUB_APP_PRIVATE_KEY holds a {type(private_key).__name__}, not an RSA key")


def create_github_api_client(token: SecretStr) -> GithubApiClient:
    return GithubApiClient(
        httpx.AsyncClient(
            base_url=_API_URL,
            headers={"Authorization": f"Bearer {token.get_secret_value()}"},
            timeout=httpx.Timeout(_TIMEOUT_SECONDS, pool=None),
        )
    )


def create_github_oauth_client() -> GithubOauthClient:
    return GithubOauthClient(
        httpx.AsyncClient(
            base_url=_OAUTH_URL, headers={"Accept": "application/json"}, timeout=_TIMEOUT_SECONDS
        )
    )


def create_github_avatar_client() -> GithubAvatarClient:
    return GithubAvatarClient(
        httpx.AsyncClient(base_url=_AVATAR_URL, timeout=_TIMEOUT_SECONDS, follow_redirects=True)
    )


_REPOSITORIES_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    databaseId
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC,
                 orderBy: {field: PUSHED_AT, direction: DESC}, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes { id pushedAt }
    }
  }
}
"""

_COMMITS_QUERY = """
query($repositoryId: ID!, $since: GitTimestamp!, $cursor: String) {
  node(id: $repositoryId) {
    ... on Repository {
      defaultBranchRef {
        target {
          ... on Commit {
            history(first: 100, since: $since, after: $cursor) {
              pageInfo { hasNextPage endCursor }
              nodes { additions authors(first: 100) { pageInfo { hasNextPage endCursor } nodes { email } } }
            }
          }
        }
      }
    }
  }
}
"""


class _Repository(BaseModel):
    id: str
    pushed_at: AwareDatetime | None = Field(alias="pushedAt")


class _PageInfo(BaseModel):
    has_next_page: bool = Field(alias="hasNextPage")
    end_cursor: str | None = Field(alias="endCursor")

    @model_validator(mode="after")
    def validate_cursor(self) -> Self:
        if self.has_next_page and not self.end_cursor:
            raise ValueError("a next page requires a non-empty cursor")
        return self

    @property
    def next_cursor(self) -> str | None:
        """Post: the non-empty cursor of the next page, or None on the last page."""
        return self.end_cursor if self.has_next_page else None


class _Repositories(BaseModel):
    page_info: _PageInfo = Field(alias="pageInfo")
    nodes: list[_Repository]


class _User(BaseModel):
    database_id: int = Field(alias="databaseId")
    repositories: _Repositories


class _UserData(BaseModel):
    user: _User | None


class _GraphqlError(BaseModel):
    message: str


class _GraphqlResponse(BaseModel):
    data: object = None
    errors: list[_GraphqlError] = Field(default_factory=list)


class _Author(BaseModel):
    email: str


class _Authors(BaseModel):
    page_info: _PageInfo = Field(alias="pageInfo")
    nodes: list[_Author]

    @model_validator(mode="after")
    def validate_complete_authors(self) -> Self:
        if self.page_info.has_next_page:
            raise ValueError("a commit requires its complete author list")
        return self


class _Commit(BaseModel):
    additions: int = Field(strict=True, ge=0)
    authors: _Authors


class _History(BaseModel):
    page_info: _PageInfo = Field(alias="pageInfo")
    nodes: list[_Commit]


class _Target(BaseModel):
    history: _History


class _Branch(BaseModel):
    target: _Target


class _RepositoryCommits(BaseModel):
    default_branch: _Branch | None = Field(alias="defaultBranchRef")


class _CommitsData(BaseModel):
    node: _RepositoryCommits


def _is_pushed_since_commits_start(pushed_at: datetime | None) -> bool:
    return pushed_at is not None and pushed_at >= _COMMITS_SINCE


async def _query(
    github_client: GithubApiClient,
    query: str,
    variables: dict[str, str | None],
    headers: Mapping[str, str],
) -> object:
    try:
        response = await github_client.post(
            "/graphql", json={"query": query, "variables": variables}, headers=headers
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise GithubRequestError("GitHub could not answer the GraphQL query") from error
    try:
        result = _GraphqlResponse.model_validate_json(response.content)
    except ValidationError as error:
        raise GithubRequestError("GitHub returned an invalid GraphQL response") from error
    if result.errors or result.data is None:
        raise GithubRequestError("GitHub could not complete the profile lookup")
    return result.data


async def _count_repository_lines_added_by_agent(
    github_client: GithubApiClient, repository_node_id: str, headers: Mapping[str, str]
) -> Counter[Agent]:
    lines_added_by_agent: Counter[Agent] = Counter()
    cursor: str | None = None
    seen_cursors: set[str] = set()
    while True:
        variables = {
            "repositoryId": repository_node_id,
            "since": _COMMITS_SINCE.isoformat(),
            "cursor": cursor,
        }
        try:
            data = _CommitsData.model_validate(
                await _query(github_client, _COMMITS_QUERY, variables, headers)
            )
        except ValidationError as error:
            raise GithubRequestError("GitHub returned invalid commit data") from error
        if data.node.default_branch is None:
            return lines_added_by_agent
        history = data.node.default_branch.target.history
        for commit in history.nodes:
            agent = find_agent(author.email for author in commit.authors.nodes)
            if agent is not None:
                lines_added_by_agent[agent] += commit.additions
        next_cursor = history.page_info.next_cursor
        if next_cursor is None:
            return lines_added_by_agent
        if next_cursor in seen_cursors:
            raise GithubRequestError("GitHub repeated a commit pagination cursor")
        seen_cursors.add(next_cursor)
        cursor = next_cursor


@dataclass(frozen=True)
class _PublicRepositories:
    github_id: GithubUserId
    repository_node_ids: tuple[str, ...]


async def _fetch_public_repositories(
    github_client: GithubApiClient, login: VerifiedGithubUsername
) -> _PublicRepositories:
    """Post: the account and its public non-fork repositories pushed since 2025."""
    repository_node_ids: list[str] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    while True:
        try:
            data = _UserData.model_validate(
                await _query(
                    github_client, _REPOSITORIES_QUERY, {"login": login, "cursor": cursor}, {}
                )
            )
        except ValidationError as error:
            raise GithubRequestError("GitHub returned invalid repository data") from error
        if data.user is None:
            raise ProfileNotFoundError(f"no GitHub user named {login!r}")
        page = data.user.repositories
        repository_node_ids.extend(
            repository.id
            for repository in page.nodes
            if _is_pushed_since_commits_start(repository.pushed_at)
        )
        next_cursor = page.page_info.next_cursor
        if next_cursor is None or any(
            repository.pushed_at is not None
            and not _is_pushed_since_commits_start(repository.pushed_at)
            for repository in page.nodes
        ):
            return _PublicRepositories(
                GithubUserId(data.user.database_id), tuple(repository_node_ids)
            )
        if next_cursor in seen_cursors:
            raise GithubRequestError("GitHub repeated a repository pagination cursor")
        seen_cursors.add(next_cursor)
        cursor = next_cursor


async def _count_repositories_lines_added_by_agent(
    github_client: GithubApiClient, repository_node_ids: tuple[str, ...], headers: Mapping[str, str]
) -> list[Counter[Agent]]:
    """Post: one count per repository, in the order of repository_node_ids."""
    pending_repositories = iter(enumerate(repository_node_ids))
    counts: list[Counter[Agent]] = [Counter() for _ in repository_node_ids]

    async def count_next_repositories() -> None:
        for index, repository_node_id in pending_repositories:
            counts[index] = await _count_repository_lines_added_by_agent(
                github_client, repository_node_id, headers
            )

    workers = [
        asyncio.create_task(count_next_repositories())
        for _ in range(min(_MAXIMUM_CONCURRENT_REPOSITORIES, len(repository_node_ids)))
    ]
    try:
        await asyncio.gather(*workers)
        return counts
    finally:
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)


async def fetch_github_profile(
    github_client: GithubApiClient, login: VerifiedGithubUsername
) -> GithubProfile:
    """Post: lines added by each agent in commits since 2025 across public non-fork repositories,
    with no private repositories, or ProfileNotFoundError. Failed or incomplete GitHub responses
    raise GithubRequestError."""
    public_repositories = await _fetch_public_repositories(github_client, login)
    counts = await _count_repositories_lines_added_by_agent(
        github_client, public_repositories.repository_node_ids, {}
    )
    return GithubProfile(
        public_repositories.github_id, login, MappingProxyType(dict(sum(counts, Counter()))), ()
    )


class _Account(BaseModel):
    id: int
    login: str = Field(pattern=GITHUB_LOGIN_PATTERN)
    type: Literal["User", "Organization"]


class _Installation(BaseModel):
    id: int
    account: _Account
    suspended_at: str | None


class _InstallationToken(BaseModel):
    token: SecretStr


class _Owner(BaseModel):
    id: int


class _InstallationRepository(BaseModel):
    id: int = Field(gt=0)
    node_id: str
    private: bool
    fork: bool
    pushed_at: AwareDatetime | None
    owner: _Owner


class _InstallationRepositories(BaseModel):
    total_count: int = Field(ge=0)
    repositories: list[_InstallationRepository]


_INSTALLATION_TOKEN = TypeAdapter(_InstallationToken)
_INSTALLATION_REPOSITORIES = TypeAdapter(_InstallationRepositories)


async def _request_rest[Body](
    client: GithubApiClient | GithubOauthClient,
    request: httpx.Request,
    body_adapter: TypeAdapter[Body],
) -> Body:
    try:
        response = await client.send(request)
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise GithubRequestError(
            f"GitHub could not complete {request.method} {request.url.path}"
        ) from error
    try:
        return body_adapter.validate_json(response.content)
    except ValidationError as error:
        raise GithubRequestError(f"GitHub answered {request.url.path} unexpectedly") from error


def _app_authorization(github_app: GithubApp, now: datetime) -> dict[str, str]:
    app_token = jwt.encode(
        {
            "iat": int((now - _APP_TOKEN_ISSUED_EARLIER).timestamp()),
            "exp": int((now + _APP_TOKEN_LIFETIME).timestamp()),
            "iss": str(github_app.id),
        },
        github_app.private_key,
        algorithm="RS256",
    )
    return {**_REST_HEADERS, "Authorization": f"Bearer {app_token}"}


async def _fetch_installation(
    github_client: GithubApiClient, app_authorization: Mapping[str, str], path: str
) -> _Installation | None:
    """Post: the installation at path, or None when GitHub has no such installation."""
    request = github_client.build_request("GET", path, headers=app_authorization)
    try:
        response = await github_client.send(request)
    except httpx.HTTPError as error:
        raise GithubRequestError(f"GitHub could not look up {path}") from error
    if response.status_code != httpx.codes.NOT_FOUND:
        try:
            response.raise_for_status()
            return _Installation.model_validate_json(response.content)
        except (httpx.HTTPError, ValidationError) as error:
            raise GithubRequestError(f"GitHub answered {path} unexpectedly") from error
    return None


async def _fetch_installation_repositories(
    github_client: GithubApiClient, installation_authorization: Mapping[str, str]
) -> list[_InstallationRepository]:
    repositories: list[_InstallationRepository] = []
    page = 1
    while True:
        request = github_client.build_request(
            "GET",
            "/installation/repositories",
            params={"per_page": _REPOSITORIES_PER_PAGE, "page": page},
            headers=installation_authorization,
        )
        body = await _request_rest(github_client, request, _INSTALLATION_REPOSITORIES)
        repositories.extend(body.repositories)
        if len(repositories) >= body.total_count or not body.repositories:
            return repositories
        page += 1


async def fetch_personal_installation(
    github_client: GithubApiClient,
    github_app: GithubApp,
    installation_id: InstallationId,
    now: datetime,
) -> PersonalInstallation:
    """Post: the installation's personal account, InstallationNotFoundError when the app has no
    such installation, or OrganizationInstallationError for an organization's installation."""
    installation = await _fetch_installation(
        github_client,
        _app_authorization(github_app, now),
        f"/app/installations/{installation_id}",
    )
    if installation is not None:
        if installation.account.type == "Organization":
            raise OrganizationInstallationError(
                f"GitToken scans personal accounts only, and {installation.account.login} is an "
                f"organization. Uninstall the GitHub App from {installation.account.login}'s "
                "settings."
            )
        return PersonalInstallation(
            GithubUserId(installation.account.id),
            VerifiedGithubUsername(installation.account.login),
        )
    raise InstallationNotFoundError(f"the GitHub App has no installation {installation_id}")


class _UserAccessToken(BaseModel):
    access_token: SecretStr


class _BadVerificationCode(BaseModel):
    error: Literal["bad_verification_code"]


class _AuthenticatedUser(BaseModel):
    id: int


_ACCESS_TOKEN_ANSWER = TypeAdapter(_UserAccessToken | _BadVerificationCode)
_AUTHENTICATED_USER = TypeAdapter(_AuthenticatedUser)


async def _revoke_user_token(
    github_client: GithubApiClient, github_app: GithubApp, access_token: str
) -> None:
    try:
        response = await github_client.request(
            "DELETE",
            f"/applications/{github_app.client_id}/token",
            json={"access_token": access_token},
            headers=_REST_HEADERS,
            auth=httpx.BasicAuth(github_app.client_id, github_app.client_secret.get_secret_value()),
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise GithubRequestError("GitHub could not revoke the user's token") from error


async def fetch_authorizing_user_id(
    oauth_client: GithubOauthClient,
    github_client: GithubApiClient,
    github_app: GithubApp,
    code: GithubAuthorizationCode,
) -> GithubUserId:
    """Post: the id of the GitHub user who authorized the app with code, or
    InvalidAuthorizationCodeError for a used, expired or forged code. Any other OAuth answer
    raises GithubRequestError. The user's token is revoked whether or not reading the user
    worked."""
    token_request = oauth_client.build_request(
        "POST",
        "/login/oauth/access_token",
        data={
            "client_id": github_app.client_id,
            "client_secret": github_app.client_secret.get_secret_value(),
            "code": code,
        },
    )
    answer = await _request_rest(oauth_client, token_request, _ACCESS_TOKEN_ANSWER)
    if isinstance(answer, _BadVerificationCode):
        raise InvalidAuthorizationCodeError("The GitHub authorization code is used or expired")
    access_token = answer.access_token.get_secret_value()
    user_request = github_client.build_request(
        "GET", "/user", headers={**_REST_HEADERS, "Authorization": f"Bearer {access_token}"}
    )
    try:
        user = await _request_rest(github_client, user_request, _AUTHENTICATED_USER)
    finally:
        await _revoke_user_token(github_client, github_app, access_token)
    return GithubUserId(user.id)


async def _revoke_installation_token(
    github_client: GithubApiClient, installation_authorization: Mapping[str, str]
) -> None:
    try:
        response = await github_client.delete(
            "/installation/token", headers=installation_authorization
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise GithubRequestError("GitHub could not revoke the installation token") from error


async def fetch_private_repositories(
    github_client: GithubApiClient, github_app: GithubApp, profile: GithubProfile, now: datetime
) -> tuple[PrivateRepository, ...]:
    """Post: lines added by each agent since 2025 in every private non-fork repository the
    profile's account owns and granted to the app; empty when the account has not installed it
    or GitHub suspended the installation. The installation token is revoked before returning."""
    installation = await _fetch_installation(
        github_client, _app_authorization(github_app, now), f"/users/{profile.login}/installation"
    )
    if installation is not None and installation.suspended_at is None:
        if installation.account.id != profile.github_id:
            raise GithubRequestError(f"the installation of {profile.login!r} is on another account")
        token_request = github_client.build_request(
            "POST",
            f"/app/installations/{installation.id}/access_tokens",
            headers=_app_authorization(github_app, now),
        )
        installation_token = await _request_rest(github_client, token_request, _INSTALLATION_TOKEN)
        installation_authorization = {
            **_REST_HEADERS,
            "Authorization": f"Bearer {installation_token.token.get_secret_value()}",
        }
        repositories = [
            repository
            for repository in await _fetch_installation_repositories(
                github_client, installation_authorization
            )
            if repository.private
            and not repository.fork
            and repository.owner.id == profile.github_id
            and _is_pushed_since_commits_start(repository.pushed_at)
        ]
        counts = await _count_repositories_lines_added_by_agent(
            github_client,
            tuple(repository.node_id for repository in repositories),
            installation_authorization,
        )
        await _revoke_installation_token(github_client, installation_authorization)
        return tuple(
            PrivateRepository(RepositoryId(repository.id), MappingProxyType(dict(count)))
            for repository, count in zip(repositories, counts, strict=True)
        )
    return ()


class _WebhookAction(BaseModel):
    action: str


class _InstalledAccount(BaseModel):
    account: _Account


class _InstallationEvent(BaseModel):
    installation: _InstalledAccount


class _RepositoryReference(BaseModel):
    id: int = Field(gt=0)


class _RepositoriesRemovedEvent(BaseModel):
    repositories_removed: list[_RepositoryReference] = Field(min_length=1)


class _RepositoryEvent(BaseModel):
    repository: _RepositoryReference


def _parse_signed_webhook(event_name: str, payload: bytes) -> ConsentWithdrawal | None:
    if event_name in {"installation", "installation_repositories", "repository"}:
        match event_name, _WebhookAction.model_validate_json(payload).action:
            case "installation", "deleted" | "suspend":
                account = _InstallationEvent.model_validate_json(payload).installation.account
                if account.type == "User":
                    return AccountDisconnected(GithubUserId(account.id))
            case "installation_repositories", "removed":
                first_repository, *other_repositories = (
                    _RepositoriesRemovedEvent.model_validate_json(payload).repositories_removed
                )
                return RepositoriesRevoked(
                    (
                        RepositoryId(first_repository.id),
                        *(RepositoryId(repository.id) for repository in other_repositories),
                    )
                )
            case "repository", "publicized" | "deleted" | "transferred":
                repository = _RepositoryEvent.model_validate_json(payload).repository
                return RepositoriesRevoked((RepositoryId(repository.id),))
    return None


def parse_webhook(
    webhook_secret: SecretStr, event_name: str, signature: str, payload: bytes
) -> ConsentWithdrawal | None:
    """Post: the consent the event withdraws, None for an event that withdraws nothing, or
    InvalidWebhookError when the payload is not signed with webhook_secret or is malformed."""
    expected_signature = (
        b"sha256="
        + hmac.new(webhook_secret.get_secret_value().encode(), payload, sha256).hexdigest().encode()
    )
    # Starlette decodes headers as latin-1; bytes keep a non-ASCII header a mismatch, not a crash.
    if not hmac.compare_digest(expected_signature, signature.encode("latin-1")):
        raise InvalidWebhookError("the webhook signature does not match the payload")
    try:
        return _parse_signed_webhook(event_name, payload)
    except ValidationError as error:
        raise InvalidWebhookError(f"the {event_name!r} webhook has an unexpected shape") from error


async def fetch_avatar(avatar_client: GithubAvatarClient, login: VerifiedGithubUsername) -> Avatar:
    """Post: the user's avatar image, or GithubRequestError for a failed or non-image answer."""
    try:
        response = await avatar_client.get(f"/{login}", params={"size": _AVATAR_SIZE_PIXELS})
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise GithubRequestError(f"GitHub could not serve the avatar of {login!r}") from error
    media_type = response.headers.get("Content-Type", "").split(";")[0].strip()
    if media_type not in _AVATAR_MEDIA_TYPES:
        raise GithubRequestError(f"GitHub returned an avatar of type {media_type!r}")
    return Avatar(response.content)
