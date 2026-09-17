"""Cliente HTTP do Jira Cloud (OAuth 2.0 3LO + REST v3 + Agile 1.0)."""

from __future__ import annotations

import base64
from datetime import date, datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from cadencia.integrations.domain.ports import (
    JiraBoard,
    JiraField,
    JiraIssue,
    JiraProject,
    JiraSite,
    JiraSprint,
    OAuthTokens,
)
from cadencia.platform.config import Settings

AUTH_BASE = "https://auth.atlassian.com"
API_BASE = "https://api.atlassian.com"

_STATUS_CATEGORY_MAP = {"new": "todo", "indeterminate": "in progress", "done": "done"}


class JiraApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"Jira API {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class HttpxJiraGateway:
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._http = http

    # ------------------------------------------------------------- OAuth ---
    def build_authorize_url(self, state: str) -> str:
        params = {
            "audience": "api.atlassian.com",
            "client_id": self._settings.jira_client_id,
            "scope": " ".join(self._settings.jira_scope_list),
            "redirect_uri": self._settings.jira_redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        }
        return f"{AUTH_BASE}/authorize?{urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthTokens:
        payload = {
            "grant_type": "authorization_code",
            "client_id": self._settings.jira_client_id,
            "client_secret": self._settings.jira_client_secret,
            "code": code,
            "redirect_uri": self._settings.jira_redirect_uri,
        }
        data = await self._post_json(f"{AUTH_BASE}/oauth/token", payload, token=None)
        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=int(data.get("expires_in", 3600)),
        )

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        payload = {
            "grant_type": "refresh_token",
            "client_id": self._settings.jira_client_id,
            "client_secret": self._settings.jira_client_secret,
            "refresh_token": refresh_token,
        }
        data = await self._post_json(f"{AUTH_BASE}/oauth/token", payload, token=None)
        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token),
            expires_in=int(data.get("expires_in", 3600)),
        )

    async def accessible_resources(self, access_token: str) -> list[JiraSite]:
        data = await self._get_json(
            f"{API_BASE}/oauth/token/accessible-resources", token=access_token
        )
        return [
            JiraSite(cloud_id=site["id"], url=site["url"], name=site.get("name", site["url"]))
            for site in data
        ]

    # -------------------------------------------------------------- REST ---
    async def list_fields(self, access_token: str, cloud_id: str) -> list[JiraField]:
        data = await self._get_json(f"{self._base(cloud_id)}/rest/api/3/field", token=access_token)
        return [
            JiraField(
                field_id=field["id"],
                name=field.get("name", ""),
                schema_type=(field.get("schema") or {}).get("type"),
            )
            for field in data
        ]

    async def list_projects(self, access_token: str, cloud_id: str) -> list[JiraProject]:
        data = await self._get_json(
            f"{self._base(cloud_id)}/rest/api/3/project/search",
            token=access_token,
            params={"maxResults": 50},
        )
        return [
            JiraProject(id=project["id"], key=project["key"], name=project.get("name", ""))
            for project in data.get("values", [])
        ]

    async def list_boards(
        self, access_token: str, cloud_id: str, project_key: str
    ) -> list[JiraBoard]:
        data = await self._get_json(
            f"{self._base(cloud_id)}/rest/agile/1.0/board",
            token=access_token,
            params={"projectKeyOrId": project_key, "maxResults": 50},
        )
        return [
            JiraBoard(id=str(board["id"]), name=board.get("name", ""))
            for board in data.get("values", [])
        ]

    async def list_sprints(
        self, access_token: str, cloud_id: str, board_id: str
    ) -> list[JiraSprint]:
        data = await self._get_json(
            f"{self._base(cloud_id)}/rest/agile/1.0/board/{board_id}/sprint",
            token=access_token,
            params={"maxResults": 50},
        )
        return [self._sprint(raw) for raw in data.get("values", [])]

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
        fields = ["summary", "issuetype", "status", "assignee", "sprint"]
        if story_points_field:
            fields.append(story_points_field)
        data = await self._get_json(
            f"{self._base(cloud_id)}/rest/api/3/search",
            token=access_token,
            params={
                "jql": f'project = "{project_key}" ORDER BY created ASC',
                "startAt": start_at,
                "maxResults": max_results,
                "fields": ",".join(fields),
            },
        )
        issues = [self._issue(raw, story_points_field) for raw in data.get("issues", [])]
        total = int(data.get("total", 0))
        has_more = start_at + len(issues) < total
        return issues, has_more

    # ----------------------------------------------------------- helpers ---
    @staticmethod
    def _base(cloud_id: str) -> str:
        return f"{API_BASE}/ex/jira/{cloud_id}"

    @staticmethod
    def _sprint(raw: dict[str, Any]) -> JiraSprint:
        return JiraSprint(
            id=str(raw["id"]),
            name=raw.get("name", ""),
            state=raw.get("state", "future"),
            start_date=_parse_date(raw.get("startDate")),
            end_date=_parse_date(raw.get("endDate")),
            goal=raw.get("goal"),
        )

    @staticmethod
    def _issue(raw: dict[str, Any], story_points_field: str | None) -> JiraIssue:
        fields = raw.get("fields") or {}
        status = fields.get("status") or {}
        category_key = ((status.get("statusCategory") or {}).get("key") or "new").lower()
        sprint_raw = fields.get("sprint") or []
        if isinstance(sprint_raw, dict):
            sprint_raw = [sprint_raw]
        points_raw = fields.get(story_points_field) if story_points_field else None
        return JiraIssue(
            external_id=str(raw.get("id", raw.get("key", ""))),
            key=str(raw.get("key", "")),
            summary=str(fields.get("summary", "")),
            issue_type=str(((fields.get("issuetype") or {}).get("name")) or "Task"),
            status_name=str(status.get("name", "")),
            status_category=_STATUS_CATEGORY_MAP.get(category_key, "todo"),
            story_points=_parse_points(points_raw),
            sprint_ids=tuple(str(sprint["id"]) for sprint in sprint_raw if "id" in sprint),
        )

    async def _get_json(
        self, url: str, *, token: str | None, params: dict[str, Any] | None = None
    ) -> Any:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        async with self._client() as client:
            response = await client.get(url, headers=headers, params=params)
        _raise_for_status(response)
        return response.json()

    async def _post_json(self, url: str, payload: dict[str, Any], *, token: str | None) -> Any:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        async with self._client() as client:
            response = await client.post(url, headers=headers, json=payload)
        _raise_for_status(response)
        return response.json()

    def _client(self) -> httpx.AsyncClient:
        if self._http is not None:
            return _SharedClient(self._http)
        return httpx.AsyncClient(timeout=30)


class _SharedClient:
    """Adapter para reutilizar um client externo (testes) sem fecha-lo."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, *args: object) -> None:
        return None


def _raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    detail = response.text[:300]
    try:
        body = response.json()
        detail = str(body.get("errorMessages") or body.get("message") or detail)
    except ValueError:
        pass
    raise JiraApiError(response.status_code, detail)


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _parse_points(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, int | float):
        return float(raw)
    if isinstance(raw, dict) and "value" in raw:
        try:
            return float(raw["value"])
        except (TypeError, ValueError):
            return None
    return None


def basic_auth_header(email: str, api_token: str) -> str:  # pragma: no cover - utilitario
    raw = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    return f"Basic {raw}"
