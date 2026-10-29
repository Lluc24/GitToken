from dataclasses import replace
from datetime import UTC, datetime, timedelta
from time import perf_counter

from loguru import logger

from gittoken.db import (
    SupabaseClient,
    delete_account_private_repositories,
    delete_private_repositories,
    delete_profile_saved_before,
    delete_renamed_user,
    fetch_cached_profile,
    fetch_leaderboard,
    fetch_stored_profiles,
    save_profile,
    save_total_tokens,
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
    fetch_private_repositories,
)
from gittoken.telemetry import tracer

# A verified owner can authorize again at will, so a profile scanned this recently is kept to
# spare the shared GitHub rate limit.
_MINIMUM_RESCAN_INTERVAL = timedelta(minutes=1)


async def lookup_profile(
    github_client: GithubApiClient,
    supabase_client: SupabaseClient,
    github_app: GithubApp | None,
    login: VerifiedGithubUsername,
) -> GithubProfile:
    """Post: the cached profile, or a fresh scan that also covers the private repositories the
    account granted when github_app is configured."""
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
                profile = await fetch_github_profile(github_client, login)
                if github_app is not None:
                    profile = replace(
                        profile,
                        private_repositories=await fetch_private_repositories(
                            github_client, github_app, profile, now
                        ),
                    )
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
    """Post: the withdrawn private repositories are forgotten and every affected account's
    leaderboard total is recomputed from what remains. If the recompute fails after the delete, a
    redelivered disconnect repairs the total; a repository revocation waits for the next scan."""
    started_at = perf_counter()
    try:
        match withdrawal:
            case AccountDisconnected(github_id):
                await delete_account_private_repositories(supabase_client, github_id)
                affected_github_ids = frozenset({github_id})
            case RepositoriesRevoked(repository_ids):
                affected_github_ids = await delete_private_repositories(
                    supabase_client, repository_ids
                )
        if affected_github_ids:
            for profile in await fetch_stored_profiles(supabase_client, affected_github_ids):
                await save_total_tokens(supabase_client, profile)
    except ProfileStoreError as error:
        logger.bind(
            event="consent_withdrawal_error",
            withdrawal_type=type(withdrawal).__name__,
            error_type=type(error).__name__,
            duration_seconds=perf_counter() - started_at,
        ).warning("Private repositories could not be forgotten")
        raise
    logger.bind(
        event="consent_withdrawn",
        withdrawal_type=type(withdrawal).__name__,
        affected_account_count=len(affected_github_ids),
        duration_seconds=perf_counter() - started_at,
    ).info("Private repositories forgotten")


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
