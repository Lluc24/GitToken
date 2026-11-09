from collections.abc import Callable

import httpx
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from gittoken import api
from gittoken.slack import SlackActivityClient
from pydantic import SecretStr

_WEBHOOK_URL = "https://hooks.slack.test/services/T0/B0/secret"

type SlackHandler = Callable[[httpx.Request], httpx.Response]


def _create_app(
    monkeypatch: pytest.MonkeyPatch, slack_webhook_url: str, handle_slack: SlackHandler
) -> FastAPI:
    monkeypatch.setenv("SLACK_ACTIVITY_WEBHOOK_URL", slack_webhook_url)

    def create_mock_slack_client(webhook_url: SecretStr) -> SlackActivityClient:
        transport = httpx.MockTransport(handle_slack)
        return SlackActivityClient(httpx.AsyncClient(transport=transport), webhook_url)

    monkeypatch.setattr(api, "create_slack_activity_client", create_mock_slack_client)
    return api.create_app()


def _post_search(app: FastAPI, login: str) -> httpx.Response:
    with TestClient(app) as client:
        return client.post("/v1/events/profile-search", json={"login": login})


def _reject(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"unexpected Slack request to {request.url}")


def _answer_server_error(_: httpx.Request) -> httpx.Response:
    return httpx.Response(500)


def _time_out(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectTimeout("timed out", request=request)


def test_profile_search_posts_the_login_to_slack(monkeypatch: pytest.MonkeyPatch) -> None:
    slack_requests: list[httpx.Request] = []

    def accept(request: httpx.Request) -> httpx.Response:
        slack_requests.append(request)
        return httpx.Response(200, text="ok")

    response = _post_search(_create_app(monkeypatch, _WEBHOOK_URL, accept), "octocat")

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert [str(request.url) for request in slack_requests] == [_WEBHOOK_URL]
    assert slack_requests[0].read() == b'{"text":"GitToken profile search: octocat"}'


def test_profile_search_without_webhook_url_sends_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _post_search(_create_app(monkeypatch, "", _reject), "octocat")

    assert response.status_code == status.HTTP_202_ACCEPTED


@pytest.mark.parametrize("handle_slack", [_answer_server_error, _time_out])
def test_profile_search_tolerates_slack_failure(
    monkeypatch: pytest.MonkeyPatch, handle_slack: SlackHandler
) -> None:
    response = _post_search(_create_app(monkeypatch, _WEBHOOK_URL, handle_slack), "octocat")

    assert response.status_code == status.HTTP_202_ACCEPTED


def test_profile_search_rejects_an_invalid_login(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _post_search(_create_app(monkeypatch, _WEBHOOK_URL, _reject), "<!channel>")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
