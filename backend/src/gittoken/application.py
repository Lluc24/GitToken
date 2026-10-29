from datetime import UTC, datetime
from time import perf_counter

import httpx
from loguru import logger

from gittoken.db import (
    SupabaseClient,
    delete_renamed_user,
    fetch_cached_profile,
    fetch_leaderboard,
    save_profile,
)
from gittoken.domain import (
    GithubProfile,
    GithubRequestError,
    LeaderboardEntry,
    ProfileNotFoundError,
    ProfileStoreError,
    VerifiedGithubUsername,
)
from gittoken.github import fetch_github_profile
from gittoken.telemetry import tracer


async def lookup_profile(
    github_token: str, supabase_client: SupabaseClient, login: VerifiedGithubUsername
) -> GithubProfile:
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
                profile = await fetch_github_profile(github_token, login)
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
    except (httpx.HTTPError, GithubRequestError, ProfileStoreError) as error:
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
