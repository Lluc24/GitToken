import asyncio
from dataclasses import dataclass

import httpx
from pydantic import SecretStr

from gittoken.domain import SlackNotificationError, VerifiedGithubUsername

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
    """Post: Slack accepted one message naming login within two seconds, or
    SlackNotificationError is raised without the webhook URL in its message."""
    try:
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            response = await client.http.post(
                client.webhook_url.get_secret_value(),
                json={"text": f"GitToken profile search: {login}"},
            )
        response.raise_for_status()
    except (httpx.HTTPError, TimeoutError) as error:
        raise SlackNotificationError(type(error).__name__) from None
