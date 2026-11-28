from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from datetime import UTC, date, datetime, timedelta
from time import perf_counter

import sentry_sdk
from loguru import logger

from gittoken.db import (
    SupabaseClient,
    delete_profile,
    delete_profile_saved_before,
    delete_profiles_granting,
    delete_renamed_user,
    fetch_cached_profile,
    fetch_leaderboard,
    save_profile,
)
from gittoken.domain import (
    AccountDisconnected,
    Avatar,
    ConsentWithdrawal,
    GithubProfile,
    GithubRequestError,
    InstallationAuthorization,
    InstallationId,
    LeaderboardEntry,
    ProfileNotFoundError,
    ProfileStoreError,
    RepositoriesRevoked,
    SlackNotificationError,
    VerifiedGithubUsername,
)
from gittoken.github import (
    GithubApiClient,
    GithubApp,
    GithubAvatarClient,
    GithubOauthClient,
    fetch_authorizing_user_id,
    fetch_avatar,
    fetch_github_profile,
    fetch_personal_installation,
)
from gittoken.slack import SlackActivityClient, notify_profile_search

# A verified owner can authorize again at will, so a profile scanned this recently is kept to
# spare the shared GitHub rate limit.
_MINIMUM_RESCAN_INTERVAL = timedelta(minutes=1)


def today_utc() -> date:
    return datetime.now(UTC).date()


@contextmanager
def _logged_failure(
    event: str, message: str, failures: tuple[type[Exception], ...], **fields: object
) -> Iterator[Callable[[], float]]:
    """Post: yields the seconds elapsed since entry; any of failures raised inside is logged as a
    warning with its type and duration, then re-raised."""
    started_at = perf_counter()

    def elapsed_seconds() -> float:
        return perf_counter() - started_at

    try:
        yield elapsed_seconds
    except failures as error:
        logger.bind(
            event=event,
            error_type=type(error).__name__,
            duration_seconds=elapsed_seconds(),
            **fields,
        ).warning(message)
        raise


async def lookup_profile(
    github_client: GithubApiClient,
    supabase_client: SupabaseClient,
    github_app: GithubApp,
    login: VerifiedGithubUsername,
) -> GithubProfile:
    """Post: the cached profile, or a fresh scan that also covers the private repositories the
    account granted."""
    now = datetime.now(UTC)
    with (
        sentry_sdk.new_scope(),
        sentry_sdk.start_transaction(op="profile.lookup", name="lookup_profile"),
        _logged_failure(
            "profile_upstream_error",
            "Profile lookup failed",
            (GithubRequestError, ProfileStoreError),
        ) as elapsed_seconds,
    ):
        try:
            with sentry_sdk.start_span(name="cache.supabase.read"):
                profile = await fetch_cached_profile(supabase_client, login, now)
            cache_hit = profile is not None
            if profile is None:
                with sentry_sdk.start_span(name="github.scan"):
                    profile = await fetch_github_profile(github_client, github_app, login, now)
                with sentry_sdk.start_span(name="profile.persist"):
                    await delete_renamed_user(supabase_client, profile)
                    await save_profile(supabase_client, profile, now)
        except ProfileNotFoundError:
            logger.bind(event="profile_not_found", duration_seconds=elapsed_seconds()).info(
                "Profile lookup returned no user"
            )
            raise
    logger.bind(
        event="profile_lookup", cache_hit=cache_hit, duration_seconds=elapsed_seconds()
    ).info("Profile lookup completed")
    return profile


async def fetch_fresh_leaderboard(supabase_client: SupabaseClient) -> tuple[LeaderboardEntry, ...]:
    return await fetch_leaderboard(supabase_client, datetime.now(UTC))


async def fetch_profile_avatar(
    avatar_client: GithubAvatarClient, login: VerifiedGithubUsername
) -> Avatar:
    with _logged_failure("avatar_upstream_error", "Avatar fetch failed", (GithubRequestError,)):
        return await fetch_avatar(avatar_client, login)


async def withdraw_consent(supabase_client: SupabaseClient, withdrawal: ConsentWithdrawal) -> None:
    """Post: no saved profile covers the withdrawn private repositories, so the next lookup of each
    affected account rescans it without them. A scan already running when the consent is withdrawn
    can save them again until the account's next rescan."""
    withdrawal_type = type(withdrawal).__name__
    with _logged_failure(
        "consent_withdrawal_error",
        "Profiles covering withdrawn repositories could not be deleted",
        (ProfileStoreError,),
        withdrawal_type=withdrawal_type,
    ) as elapsed_seconds:
        match withdrawal:
            case AccountDisconnected(github_id):
                await delete_profile(supabase_client, github_id)
            case RepositoriesRevoked(repository_ids):
                await delete_profiles_granting(supabase_client, repository_ids)
    logger.bind(
        event="consent_withdrawn",
        withdrawal_type=withdrawal_type,
        duration_seconds=elapsed_seconds(),
    ).info("Profiles covering withdrawn repositories deleted")


async def find_installation_login(
    github_client: GithubApiClient, github_app: GithubApp, installation_id: InstallationId
) -> VerifiedGithubUsername:
    """Post: the installation's personal login; nothing is changed."""
    installation = await fetch_personal_installation(
        github_client, github_app, installation_id, datetime.now(UTC)
    )
    return installation.login


async def finish_authorized_installation(
    github_client: GithubApiClient,
    oauth_client: GithubOauthClient,
    supabase_client: SupabaseClient,
    github_app: GithubApp,
    authorization: InstallationAuthorization,
) -> VerifiedGithubUsername:
    """Post: the installation's personal login. Its cached profile is dropped, so the next lookup
    rescans it, only when the user who authorized the app is the installation's own account and
    the profile is over a minute old."""
    now = datetime.now(UTC)
    installation = await fetch_personal_installation(
        github_client, github_app, authorization.installation_id, now
    )
    authorizing_user_id = await fetch_authorizing_user_id(
        oauth_client, github_client, github_app, authorization.code
    )
    if authorizing_user_id == installation.github_id:
        await delete_profile_saved_before(
            supabase_client, installation.github_id, now - _MINIMUM_RESCAN_INTERVAL
        )
    else:
        logger.bind(event="installation_authorized_by_another_user").warning(
            "Installation setup authorized by a user other than its account"
        )
    return installation.login


async def report_profile_search(
    slack_client: SlackActivityClient, login: VerifiedGithubUsername
) -> None:
    """Post: Slack was told about the search, or the failure was logged. The activity feed is
    best effort, so its failure never reaches the visitor; the log leaves out the login, as
    warnings are forwarded to Sentry."""
    with (
        suppress(SlackNotificationError),
        _logged_failure(
            "slack_activity_error",
            "Slack activity notification failed",
            (SlackNotificationError,),
        ),
    ):
        await notify_profile_search(slack_client, login)
