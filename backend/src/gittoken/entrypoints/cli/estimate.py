import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import AwareDatetime, SecretStr
from pydantic_settings import BaseSettings, CliPositionalArg, SettingsConfigDict

from gittoken.application.estimate_profile_tokens import EstimateProfileTokens
from gittoken.application.ports import ProfileNotFoundError
from gittoken.domain.estimator import ProfileEstimate
from gittoken.domain.github_login import GithubLogin, InvalidGithubLoginError
from gittoken.entrypoints.cli.data_files import load_agent_signatures, load_estimator_version
from gittoken.integrations.github_graphql import GithubGraphqlClient

_GITHUB_TIMEOUT_SECONDS = 30
_EXIT_CODE_PROFILE_NOT_FOUND = 1
_EXIT_CODE_INVALID_LOGIN = 2


class EstimateSettings(BaseSettings):
    model_config = SettingsConfigDict(cli_parse_args=True, cli_kebab_case=True, cli_prog_name="gittoken-estimate")

    login: CliPositionalArg[str]
    github_token: SecretStr
    estimator_version_file: Path = Path("data/estimator_v0.yaml")
    agent_signatures_file: Path = Path("data/signatures.yaml")
    commits_since: AwareDatetime = datetime(2025, 1, 1, tzinfo=UTC)


def _print_estimate(estimate: ProfileEstimate) -> None:
    print(f"{estimate.login.value}: {estimate.total_tokens:,} tokens (estimator {estimate.estimator_version})")
    print(f"{'agent':<14}{'commits':>9}{'lines added':>13}{'tokens':>18}")
    for agent_estimate in estimate.agent_estimates:
        print(
            f"{agent_estimate.agent:<14}{agent_estimate.commit_count:>9,}"
            f"{agent_estimate.lines_added:>13,}{agent_estimate.tokens:>18,}"
        )


async def _estimate(settings: EstimateSettings, login: GithubLogin) -> ProfileEstimate:
    async with httpx.AsyncClient(timeout=_GITHUB_TIMEOUT_SECONDS) as http_client:
        use_case = EstimateProfileTokens(
            github=GithubGraphqlClient(http_client, settings.github_token.get_secret_value()),
            signatures=load_agent_signatures(settings.agent_signatures_file),
            version=load_estimator_version(settings.estimator_version_file),
            commits_since=settings.commits_since,
        )
        return await use_case.execute(login)


def main() -> int:
    settings = EstimateSettings()
    try:
        login = GithubLogin(settings.login)
    except InvalidGithubLoginError as error:
        print(f"invalid login: {error}", file=sys.stderr)
        return _EXIT_CODE_INVALID_LOGIN
    try:
        estimate = asyncio.run(_estimate(settings, login))
    except ProfileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return _EXIT_CODE_PROFILE_NOT_FOUND
    _print_estimate(estimate)
    return 0
