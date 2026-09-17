"""Agregados do contexto integrations (Jira)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from cadencia.shared.domain import AggregateRoot, DomainEvent
from cadencia.shared.errors import ConflictError
from cadencia.shared.ids import uuid7


@dataclass(frozen=True)
class IntegrationConnected(DomainEvent):
    event_type = "integration.connected"
    provider: str
    site_url: str


@dataclass(frozen=True)
class IntegrationDisconnected(DomainEvent):
    event_type = "integration.disconnected"
    provider: str


class Integration(AggregateRoot):
    def __init__(
        self,
        *,
        workspace_id: uuid.UUID,
        provider: str,
        cloud_id: str,
        site_url: str,
        status: str = "CONNECTED",
        field_map: dict[str, str] | None = None,
        created_at: datetime,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.workspace_id = workspace_id
        self.provider = provider
        self.cloud_id = cloud_id
        self.site_url = site_url
        self.status = status
        self.field_map: dict[str, str] = field_map or {}
        self.created_at = created_at

    @classmethod
    def connect(
        cls,
        *,
        workspace_id: uuid.UUID,
        provider: str,
        cloud_id: str,
        site_url: str,
        now: datetime,
    ) -> Integration:
        integration = cls(
            workspace_id=workspace_id,
            provider=provider,
            cloud_id=cloud_id,
            site_url=site_url,
            created_at=now,
        )
        integration._record(IntegrationConnected(provider=provider, site_url=site_url))
        return integration

    def set_field_map(self, field_map: dict[str, str]) -> None:
        self.field_map = {**self.field_map, **field_map}

    def disconnect(self) -> None:
        if self.status == "DISCONNECTED":
            raise ConflictError("Integração já desconectada", code="INTEGRATION_DISCONNECTED")
        self.status = "DISCONNECTED"
        self._record(IntegrationDisconnected(provider=self.provider))


@dataclass
class SyncCursor:
    project_key: str
    start_at: int = 0
    board_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "project_key": self.project_key,
            "start_at": self.start_at,
            "board_id": self.board_id,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> SyncCursor:
        start_at_raw = raw.get("start_at", 0)
        start_at = int(start_at_raw) if isinstance(start_at_raw, int | float | str) else 0
        return cls(
            project_key=str(raw.get("project_key", "")),
            start_at=start_at,
            board_id=str(raw["board_id"]) if raw.get("board_id") else None,
        )


class SyncJob(AggregateRoot):
    def __init__(
        self,
        *,
        connection_id: uuid.UUID,
        job_type: str,
        state: str,
        cursor: SyncCursor,
        imported_count: int = 0,
        last_error: str | None = None,
        created_at: datetime,
        updated_at: datetime | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.connection_id = connection_id
        self.job_type = job_type
        self.state = state
        self.cursor = cursor
        self.imported_count = imported_count
        self.last_error = last_error
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def start_import(cls, *, connection_id: uuid.UUID, project_key: str, now: datetime) -> SyncJob:
        return cls(
            connection_id=connection_id,
            job_type="IMPORT_PROJECT",
            state="PENDING",
            cursor=SyncCursor(project_key=project_key),
            created_at=now,
        )

    def mark_running(self, now: datetime) -> None:
        if self.state == "DONE":
            raise ConflictError("Job já concluído", code="JOB_ALREADY_DONE")
        self.state = "RUNNING"
        self.updated_at = now

    def advance(self, *, imported: int, next_start_at: int, has_more: bool, now: datetime) -> None:
        self.imported_count += imported
        self.cursor.start_at = next_start_at
        self.state = "RUNNING" if has_more else "DONE"
        self.updated_at = now

    def fail(self, *, error: str, now: datetime) -> None:
        self.state = "FAILED"
        self.last_error = error[:500]
        self.updated_at = now


def new_event_id() -> uuid.UUID:
    return uuid7()
