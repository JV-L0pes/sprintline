"""Portas de persistência do contexto integrations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from cadencia.integrations.domain.entities import Integration, SyncJob


@dataclass(frozen=True)
class StoredTokens:
    access_token: str | None
    refresh_token: str | None
    access_expires_at: datetime | None


class IntegrationRepository(Protocol):
    async def get(
        self, connection_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> Integration | None: ...
    async def get_by_id(self, connection_id: uuid.UUID) -> Integration | None: ...
    async def list_for_workspace(self, workspace_id: uuid.UUID) -> list[Integration]: ...
    async def add(self, integration: Integration) -> None: ...
    async def save(self, integration: Integration) -> None: ...
    async def delete(self, integration: Integration) -> None: ...


class TokenStore(Protocol):
    async def load(self, connection_id: uuid.UUID) -> StoredTokens | None: ...
    async def save(
        self,
        connection_id: uuid.UUID,
        *,
        access_token: str,
        refresh_token: str,
        access_expires_at: datetime,
    ) -> None: ...
    async def clear(self, connection_id: uuid.UUID) -> None: ...


class SyncJobRepository(Protocol):
    async def get(self, job_id: uuid.UUID) -> SyncJob | None: ...
    async def list_for_connection(self, connection_id: uuid.UUID) -> list[SyncJob]: ...
    async def add(self, job: SyncJob) -> None: ...
    async def save(self, job: SyncJob) -> None: ...


class ExternalMappingRepository(Protocol):
    async def find(
        self, connection_id: uuid.UUID, entity_type: str, external_id: str
    ) -> uuid.UUID | None: ...
    async def save(
        self,
        connection_id: uuid.UUID,
        entity_type: str,
        external_id: str,
        internal_id: uuid.UUID,
        field_map: dict[str, str] | None = None,
    ) -> None: ...
    async def list_by_type(
        self, connection_id: uuid.UUID, entity_type: str
    ) -> list[tuple[str, uuid.UUID]]: ...
    async def delete_for_connection(self, connection_id: uuid.UUID) -> None: ...


class WebhookEventRepository(Protocol):
    async def register(
        self, connection_id: uuid.UUID, external_event_id: str, received_at: datetime
    ) -> bool:
        """Retorna True se o evento e novo; False se já foi processado (RN-20)."""
        ...
