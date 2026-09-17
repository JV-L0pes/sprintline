"""Testes unitarios do contexto integrations (sem rede)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from cadencia.integrations.application.use_cases import (
    StartJiraOAuth,
    snap_story_points,
)
from cadencia.integrations.domain.ports import JiraSite, OAuthTokens
from cadencia.platform.config import Settings
from cadencia.platform.security import decode_state_token, webhook_token
from cadencia.shared.clock import FrozenClock, SystemClock

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


class FakeGateway:
    def build_authorize_url(self, state: str) -> str:
        return f"https://auth.example/authorize?state={state}"

    async def exchange_code(self, code: str) -> OAuthTokens:  # pragma: no cover - contrato
        return OAuthTokens(access_token=code, refresh_token=code, expires_in=3600)

    async def accessible_resources(self, access_token: str) -> list[JiraSite]:  # pragma: no cover
        return [JiraSite(cloud_id="cloud", url="https://acme.atlassian.net", name="Acme")]


def make_settings() -> Settings:
    return Settings(
        jwt_secret="unit-test-secret-unit-test-secret",
        jira_client_id="client-id",
        jira_client_secret="client-secret",
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        (0, None),
        (1, 1),
        (2.0, 2),
        (4, 3),
        (7.4, 8),
        (13, 13),
        (21, 13),
    ],
)
def test_snap_story_points_to_fibonacci(raw: float | None, expected: int | None) -> None:
    assert snap_story_points(raw) == expected


async def test_start_oauth_requires_client_id() -> None:
    settings = Settings(jwt_secret="x" * 32, jira_client_id="")
    use_case = StartJiraOAuth(FakeGateway(), settings, FrozenClock(NOW))  # type: ignore[arg-type]
    with pytest.raises(Exception, match="JIRA_CLIENT_ID"):
        await use_case.execute(workspace_id=uuid.uuid4(), user_id=uuid.uuid4())


async def test_start_oauth_builds_state_with_workspace() -> None:
    settings = make_settings()
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    use_case = StartJiraOAuth(FakeGateway(), settings, SystemClock())  # type: ignore[arg-type]

    url = await use_case.execute(workspace_id=workspace_id, user_id=user_id)

    assert "state=" in url
    state = url.split("state=")[1]
    claims = decode_state_token(state, settings=settings)
    assert claims["wid"] == str(workspace_id)
    assert claims["uid"] == str(user_id)
    assert claims["typ"] == "jira_oauth"


def test_webhook_token_is_stable_and_secret() -> None:
    settings = make_settings()
    connection_id = str(uuid.uuid4())
    first = webhook_token(connection_id, settings)
    second = webhook_token(connection_id, settings)
    assert first == second
    assert len(first) == 32
    other = webhook_token(str(uuid.uuid4()), settings)
    assert other != first
