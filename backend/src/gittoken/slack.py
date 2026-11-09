from dataclasses import dataclass

import httpx
from loguru import logger
from pydantic import SecretStr

from gittoken.domain import VerifiedGithubUsername

_TIMEOUT_SECONDS = 2


@dataclass(frozen=True)
class SlackActivityClient:
    http: httpx.AsyncClient
    webhook_url: SecretStr

    async def aclose(self) -> None:
        await self.http.aclose()


def create_slack_activity_client(webhook_url: SecretStr) -> SlackActivityClient:
    return SlackActivityClient(httpx.AsyncClient(timeout=_TIMEOUT_SECONDS), webhook_url)


async def notify_profile_search(client: SlackActivityClient, login: VerifiedGithubUsername) -> None:
    """Post: Slack was sent one message naming login, or the failure was logged.
    The activity feed is best effort, so a failure never reaches the visitor; the log names
    neither the login nor the webhook URL, as warnings are forwarded to Sentry."""
    try:
        response = await client.http.post(
            client.webhook_url.get_secret_value(),
            json={"text": f"GitToken profile search: {login}"},
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        logger.warning("Slack activity notification failed: {}", type(error).__name__)
