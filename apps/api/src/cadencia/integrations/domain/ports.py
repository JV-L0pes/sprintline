"""Porta do Jira (gateway) — implementada em infraestrutura com httpx."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    expires_in: int


@dataclass(frozen=True)
class JiraSite:
    cloud_id: str
    url: str
    name: str


@dataclass(frozen=True)
class JiraField:
    field_id: str
    name: str
    schema_type: str | None


@dataclass(frozen=True)
class JiraProject:
    id: str
    key: str
    name: str


@dataclass(frozen=True)
class JiraBoard:
    id: str
    name: str


@dataclass(frozen=True)
class JiraSprint:
    id: str
    name: str
    state: str
    start_date: date | None
    end_date: date | None
    goal: str | None


@dataclass(frozen=True)
class JiraIssue:
    external_id: str
    key: str
    summary: str
    issue_type: str
    status_name: str
    status_category: str  # "todo" | "in progress" | "done"
    story_points: float | None
    sprint_ids: tuple[str, ...]


@dataclass(frozen=True)
class TrelloMember:
    id: str
    username: str
    full_name: str


@dataclass(frozen=True)
class TrelloBoard:
    id: str
    name: str
    url: str
    closed: bool


@dataclass(frozen=True)
class TrelloList:
    id: str
    name: str
    pos: float


@dataclass(frozen=True)
class TrelloCard:
    id: str
    id_list: str
    name: str
    desc: str
    url: str
    closed: bool
    labels: tuple[str, ...]
    due: str | None


class TrelloGateway(Protocol):
    def build_authorize_url(self, return_url: str) -> str: ...

    async def member_me(self, token: str) -> TrelloMember: ...

    async def member_boards(self, token: str) -> list[TrelloBoard]: ...

    async def get_board(self, token: str, board_id: str) -> TrelloBoard | None: ...

    async def board_lists(self, token: str, board_id: str) -> list[TrelloList]: ...

    async def board_cards(self, token: str, board_id: str) -> list[TrelloCard]:
        """Retorna todos os cards abertos, ordenados por id (ordem de criacao)."""
        ...

    async def get_card(self, token: str, card_id: str) -> TrelloCard | None: ...

    async def register_webhook(
        self, token: str, board_id: str, callback_url: str, description: str
    ) -> str | None: ...


class JiraGateway(Protocol):
    def build_authorize_url(self, state: str) -> str: ...

    async def exchange_code(self, code: str) -> OAuthTokens: ...

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens: ...

    async def accessible_resources(self, access_token: str) -> list[JiraSite]: ...

    async def list_fields(self, access_token: str, cloud_id: str) -> list[JiraField]: ...

    async def list_projects(self, access_token: str, cloud_id: str) -> list[JiraProject]: ...

    async def list_boards(
        self, access_token: str, cloud_id: str, project_key: str
    ) -> list[JiraBoard]: ...

    async def list_sprints(
        self, access_token: str, cloud_id: str, board_id: str
    ) -> list[JiraSprint]: ...

    async def search_issues(
        self,
        access_token: str,
        cloud_id: str,
        project_key: str,
        *,
        start_at: int,
        max_results: int,
        story_points_field: str | None,
    ) -> tuple[list[JiraIssue], bool]: ...
