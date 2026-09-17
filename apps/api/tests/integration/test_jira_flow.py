"""Fluxo Jira com gateway fake: OAuth, descoberta, import idempotente e webhook."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from tests.conftest import create_workspace, register_and_login

from cadencia.integrations.application.use_cases import CompleteJiraOAuth
from cadencia.integrations.domain.ports import (
    JiraBoard,
    JiraField,
    JiraIssue,
    JiraProject,
    JiraSite,
    JiraSprint,
    OAuthTokens,
)
from cadencia.integrations.infrastructure.repositories import (
    SqlIntegrationRepository,
    SqlTokenStore,
)
from cadencia.integrations.infrastructure.vault import TokenVault
from cadencia.platform.security import encode_state_token, webhook_token
from cadencia.shared.clock import SystemClock

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


class FakeJiraGateway:
    def __init__(self) -> None:
        self.issues = [
            JiraIssue(
                external_id="10001",
                key="SCRUM-1",
                summary="Login com SSO",
                issue_type="Story",
                status_name="Done",
                status_category="done",
                story_points=5,
                sprint_ids=(),
            ),
            JiraIssue(
                external_id="10002",
                key="SCRUM-2",
                summary="Dashboard",
                issue_type="Task",
                status_name="In Progress",
                status_category="in progress",
                story_points=4.0,
                sprint_ids=(),
            ),
        ]

    def build_authorize_url(self, state: str) -> str:
        return f"https://auth.example/authorize?state={state}"

    async def exchange_code(self, code: str) -> OAuthTokens:
        return OAuthTokens(access_token="access-1", refresh_token="refresh-1", expires_in=3600)

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        return OAuthTokens(access_token="access-2", refresh_token=refresh_token, expires_in=3600)

    async def accessible_resources(self, access_token: str) -> list[JiraSite]:
        return [JiraSite(cloud_id="cloud-1", url="https://acme.atlassian.net", name="Acme")]

    async def list_fields(self, access_token: str, cloud_id: str) -> list[JiraField]:
        return [
            JiraField(field_id="summary", name="Summary", schema_type="string"),
            JiraField(field_id="customfield_10016", name="Story Points", schema_type="number"),
        ]

    async def list_projects(self, access_token: str, cloud_id: str) -> list[JiraProject]:
        return [JiraProject(id="1", key="SCRUM", name="Scrum")]

    async def list_boards(
        self, access_token: str, cloud_id: str, project_key: str
    ) -> list[JiraBoard]:
        return [JiraBoard(id="10", name="Scrum Board")]

    async def list_sprints(
        self, access_token: str, cloud_id: str, board_id: str
    ) -> list[JiraSprint]:
        return []

    async def search_issues(
        self,
        access_token: str,
        cloud_id: str,
        project_key: str,
        *,
        start_at: int,
        max_results: int,
        story_points_field: str | None,
    ) -> tuple[list[JiraIssue], bool]:
        window = self.issues[start_at : start_at + max_results]
        has_more = start_at + len(window) < len(self.issues)
        return window, has_more


@pytest.fixture
async def jira_gateway(api_app: Any) -> FakeJiraGateway:
    gateway = FakeJiraGateway()
    api_app.state.jira_gateway = gateway  # type: ignore[attr-defined]
    yield gateway
    if hasattr(api_app.state, "jira_gateway"):
        del api_app.state.jira_gateway  # type: ignore[attr-defined]


async def _connect_jira(api_app: Any, client: httpx.AsyncClient, headers: dict[str, str]) -> str:
    workspace = await create_workspace(client, headers, name="Jira WS")
    settings = api_app.state.settings
    original = settings.jira_client_id
    settings.jira_client_id = "test-client"
    try:
        async with api_app.state.session_factory() as session:
            state = encode_state_token(
                {
                    "typ": "jira_oauth",
                    "wid": workspace["id"],
                    "uid": "00000000-0000-0000-0000-000000000000",
                },
                settings=settings,
                now=SystemClock().now(),
            )
            view = await CompleteJiraOAuth(
                api_app.state.jira_gateway,
                SqlIntegrationRepository(session),
                SqlTokenStore(session, TokenVault(settings.fernet_key)),
                settings,
                SystemClock(),
            ).execute(code="code-1", state=state)
            await session.commit()
        assert str(view.id)
        return workspace["id"]
    finally:
        settings.jira_client_id = original


async def test_oauth_connection_and_field_discovery(
    client: httpx.AsyncClient, api_app: Any, jira_gateway: FakeJiraGateway
) -> None:
    headers = await register_and_login(client)
    workspace_id = await _connect_jira(api_app, client, headers)

    listed = await client.get(f"/api/v1/workspaces/{workspace_id}/integrations", headers=headers)
    assert listed.status_code == 200, listed.text
    integrations = listed.json()
    assert len(integrations) == 1
    connection_id = integrations[0]["id"]
    assert integrations[0]["site_url"] == "https://acme.atlassian.net"

    discovery = await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/fields",
        headers=headers,
    )
    assert discovery.status_code == 200
    assert discovery.json()["story_points_field"] == "customfield_10016"


async def test_import_is_chunked_and_idempotent(
    client: httpx.AsyncClient, api_app: Any, jira_gateway: FakeJiraGateway
) -> None:
    headers = await register_and_login(client)
    workspace_id = await _connect_jira(api_app, client, headers)
    connection_id = (
        await client.get(f"/api/v1/workspaces/{workspace_id}/integrations", headers=headers)
    ).json()[0]["id"]
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/fields",
        headers=headers,
    )

    started = await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/import",
        json={"project_key": "scrum"},
        headers=headers,
    )
    assert started.status_code == 201, started.text
    job_id = started.json()["id"]

    first = await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/jobs/{job_id}/run",
        headers=headers,
    )
    assert first.status_code == 200, first.text
    assert first.json()["state"] == "DONE"
    assert first.json()["imported_count"] == 2

    project_list = (
        await client.get(f"/api/v1/workspaces/{workspace_id}/projects", headers=headers)
    ).json()
    project = next(item for item in project_list if item["key"] == "SCRUM")
    items = (
        await client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/items", headers=headers
        )
    ).json()
    by_title = {item["title"]: item for item in items}
    assert by_title["Login com SSO"]["story_points"] == 5
    assert by_title["Login com SSO"]["status_category"] == "DONE"
    assert by_title["Dashboard"]["story_points"] == 3  # 4.0 arredonda para o Fibonacci mais próximo

    # Reexecução de job concluído e bloqueada e não duplica nada (RN-20)
    second = await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/jobs/{job_id}/run",
        headers=headers,
    )
    assert second.status_code == 409
    assert second.json()["code"] == "JOB_ALREADY_DONE"
    items_after = (
        await client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/items", headers=headers
        )
    ).json()
    assert len(items_after) == 2


async def test_webhook_dedupes_and_moves_item(
    client: httpx.AsyncClient, api_app: Any, jira_gateway: FakeJiraGateway
) -> None:
    headers = await register_and_login(client)
    workspace_id = await _connect_jira(api_app, client, headers)
    connection_id = (
        await client.get(f"/api/v1/workspaces/{workspace_id}/integrations", headers=headers)
    ).json()[0]["id"]
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/fields",
        headers=headers,
    )
    job = (
        await client.post(
            f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/import",
            json={"project_key": "SCRUM"},
            headers=headers,
        )
    ).json()
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/jobs/{job['id']}/run",
        headers=headers,
    )

    token = webhook_token(connection_id, api_app.state.settings)
    payload = {
        "webhookEvent": "jira:issue_updated",
        "timestamp": 123,
        "issue": {
            "key": "SCRUM-1",
            "fields": {"status": {"statusCategory": {"key": "indeterminate"}}},
        },
    }
    first = await client.post(
        f"/api/v1/integrations/jira/webhook/{connection_id}?token={token}", json=payload
    )
    assert first.status_code == 200
    assert first.json()["status"] == "accepted"

    second = await client.post(
        f"/api/v1/integrations/jira/webhook/{connection_id}?token={token}", json=payload
    )
    assert second.json()["status"] == "duplicate"

    project = next(
        item
        for item in (
            await client.get(f"/api/v1/workspaces/{workspace_id}/projects", headers=headers)
        ).json()
        if item["key"] == "SCRUM"
    )
    items = (
        await client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/items", headers=headers
        )
    ).json()
    updated = next(item for item in items if item["title"] == "Login com SSO")
    assert updated["status_category"] == "IN_PROGRESS"
    assert updated["done_at"] is None

    bad_token = await client.post(
        f"/api/v1/integrations/jira/webhook/{connection_id}?token=errado", json=payload
    )
    assert bad_token.status_code == 404
