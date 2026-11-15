from datetime import UTC, date, datetime, timedelta
from time import perf_counter

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
from gittoken.telemetry import tracer

# A verified owner can authorize again at will, so a profile scanned this recently is kept to
# spare the shared GitHub rate limit.
_MINIMUM_RESCAN_INTERVAL = timedelta(minutes=1)


def today_utc() -> date:
    return datetime.now(UTC).date()


async def lookup_profile(
    github_client: GithubApiClient,
    supabase_client: SupabaseClient,
    github_app: GithubApp,
    login: VerifiedGithubUsername,
) -> GithubProfile:
    """Post: the cached profile, or a fresh scan that also covers the private repositories the
    account granted."""
    started_at = perf_counter()
    now = datetime.now(UTC)
    try:
        with tracer.start_as_current_span(
            "cache.supabase.read", record_exception=False, set_status_on_exception=False
        ):
            profile = await fetch_cached_profile(supabase_client, login, now)
        cache_hit = profile is not None
        if profile is None:
            with tracer.start_as_current_span(
                "github.scan", record_exception=False, set_status_on_exception=False
            ):
                profile = await fetch_github_profile(github_client, github_app, login, now)
            with tracer.start_as_current_span(
                "profile.persist", record_exception=False, set_status_on_exception=False
            ):
                await delete_renamed_user(supabase_client, profile)
                await save_profile(supabase_client, profile, now)
    except ProfileNotFoundError:
        logger.bind(event="profile_not_found", duration_seconds=perf_counter() - started_at).info(
            "Profile lookup returned no user"
        )
        raise
    except (GithubRequestError, ProfileStoreError) as error:
        logger.bind(
            event="profile_upstream_error",
            error_type=type(error).__name__,
            duration_seconds=perf_counter() - started_at,
        ).warning("Profile lookup failed")
        raise
    logger.bind(
        event="profile_lookup",
        cache_hit=cache_hit,
        duration_seconds=perf_counter() - started_at,
    ).info("Profile lookup completed")
    return profile


async def fetch_fresh_leaderboard(supabase_client: SupabaseClient) -> tuple[LeaderboardEntry, ...]:
    return await fetch_leaderboard(supabase_client, datetime.now(UTC))


async def fetch_profile_avatar(
    avatar_client: GithubAvatarClient, login: VerifiedGithubUsername
) -> Avatar:
    started_at = perf_counter()
    try:
        avatar = await fetch_avatar(avatar_client, login)
    except GithubRequestError as error:
        logger.bind(
            event="avatar_upstream_error",
            error_type=type(error).__name__,
            duration_seconds=perf_counter() - started_at,
        ).warning("Avatar fetch failed")
        raise
    return avatar


async def withdraw_consent(supabase_client: SupabaseClient, withdrawal: ConsentWithdrawal) -> None:
    """Post: no saved profile covers the withdrawn private repositories, so the next lookup of each
    affected account rescans it without them. A scan already running when the consent is withdrawn
    can save them again until the account's next rescan."""
    started_at = perf_counter()
    try:
        match withdrawal:
            case AccountDisconnected(github_id):
                await delete_profile(supabase_client, github_id)
            case RepositoriesRevoked(repository_ids):
                await delete_profiles_granting(supabase_client, repository_ids)
    except ProfileStoreError as error:
        logger.bind(
            event="consent_withdrawal_error",
            withdrawal_type=type(withdrawal).__name__,
            error_type=type(error).__name__,
            duration_seconds=perf_counter() - started_at,
        ).warning("Profiles covering withdrawn repositories could not be deleted")
        raise
    logger.bind(
        event="consent_withdrawn",
        withdrawal_type=type(withdrawal).__name__,
        duration_seconds=perf_counter() - started_at,
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
    started_at = perf_counter()
    try:
        await notify_profile_search(slack_client, login)
    except SlackNotificationError as error:
        logger.bind(
            event="slack_activity_error",
            error_type=str(error),
            duration_seconds=perf_counter() - started_at,
        ).warning("Slack activity notification failed")
