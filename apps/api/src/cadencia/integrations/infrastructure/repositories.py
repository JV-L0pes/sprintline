"""Adaptadores SQLAlchemy das portas de integrations."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cadencia.integrations.domain.entities import Integration, SyncCursor, SyncJob
from cadencia.integrations.domain.repositories import StoredTokens
from cadencia.integrations.infrastructure import orm
from cadencia.integrations.infrastructure.vault import TokenVault
from cadencia.platform.db import ensure_utc
from cadencia.platform.events import audit_for, clock_for, recorder_for


def _integration(row: orm.IntegrationRow) -> Integration:
    return Integration(
        entity_id=row.id,
        workspace_id=row.workspace_id,
        provider=row.provider,
        cloud_id=row.cloud_id,
        site_url=row.site_url,
        status=row.status,
        field_map=dict(row.field_map or {}),
        created_at=ensure_utc(row.created_at) or row.created_at,
    )


class SqlIntegrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, connection_id: uuid.UUID, workspace_id: uuid.UUID) -> Integration | None:
        row = (
            await self._session.execute(
                sa.select(orm.IntegrationRow).where(
                    orm.IntegrationRow.id == connection_id,
                    orm.IntegrationRow.workspace_id == workspace_id,
                )
            )
        ).scalar_one_or_none()
        return _integration(row) if row else None

    async def get_by_id(self, connection_id: uuid.UUID) -> Integration | None:
        row = await self._session.get(orm.IntegrationRow, connection_id)
        return _integration(row) if row else None

    async def list_for_workspace(self, workspace_id: uuid.UUID) -> list[Integration]:
        rows = (
            (
                await self._session.execute(
                    sa.select(orm.IntegrationRow)
                    .where(orm.IntegrationRow.workspace_id == workspace_id)
                    .order_by(orm.IntegrationRow.created_at)
                )
            )
            .scalars()
            .all()
        )
        return [_integration(row) for row in rows]

    def _append_events(self, integration: Integration) -> None:
        recorder_for(self._session).append(
            integration,
            workspace_id=integration.workspace_id,
            audit=audit_for(self._session),
            occurred_at=clock_for(self._session).now(),
        )

    async def add(self, integration: Integration) -> None:
        self._session.add(
            orm.IntegrationRow(
                id=integration.id,
                workspace_id=integration.workspace_id,
                provider=integration.provider,
                cloud_id=integration.cloud_id,
                site_url=integration.site_url,
                status=integration.status,
                field_map=integration.field_map,
                created_at=integration.created_at,
            )
        )
        await self._session.flush()
        self._append_events(integration)

    async def save(self, integration: Integration) -> None:
        row = await self._session.get(orm.IntegrationRow, integration.id)
        if row is None:
            await self.add(integration)
            return
        row.status = integration.status
        row.field_map = integration.field_map
        await self._session.flush()
        self._append_events(integration)

    async def delete(self, integration: Integration) -> None:
        row = await self._session.get(orm.IntegrationRow, integration.id)
        if row is not None:
            self._append_events(integration)
            await self._session.delete(row)
            await self._session.flush()


class SqlTokenStore:
    def __init__(self, session: AsyncSession, vault: TokenVault) -> None:
        self._session = session
        self._vault = vault

    async def load(self, connection_id: uuid.UUID) -> StoredTokens | None:
        row = (
            await self._session.execute(
                sa.select(orm.IntegrationTokenRow).where(
                    orm.IntegrationTokenRow.connection_id == connection_id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return StoredTokens(
            access_token=self._vault.decrypt(row.access_token_enc),
            refresh_token=self._vault.decrypt(row.refresh_token_enc),
            access_expires_at=ensure_utc(row.access_expires_at),
        )

    async def save(
        self,
        connection_id: uuid.UUID,
        *,
        access_token: str,
        refresh_token: str,
        access_expires_at: datetime,
    ) -> None:
        row = (
            await self._session.execute(
                sa.select(orm.IntegrationTokenRow).where(
                    orm.IntegrationTokenRow.connection_id == connection_id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            self._session.add(
                orm.IntegrationTokenRow(
                    id=uuid.uuid4(),
                    connection_id=connection_id,
                    access_token_enc=self._vault.encrypt(access_token),
                    refresh_token_enc=self._vault.encrypt(refresh_token),
                    access_expires_at=access_expires_at,
                    updated_at=access_expires_at,
                )
            )
        else:
            row.access_token_enc = self._vault.encrypt(access_token)
            row.refresh_token_enc = self._vault.encrypt(refresh_token)
            row.access_expires_at = access_expires_at
            row.updated_at = access_expires_at
        await self._session.flush()

    async def clear(self, connection_id: uuid.UUID) -> None:
        await self._session.execute(
            sa.delete(orm.IntegrationTokenRow).where(
                orm.IntegrationTokenRow.connection_id == connection_id
            )
        )
        await self._session.flush()


class SqlSyncJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _job(self, row: orm.SyncJobRow) -> SyncJob:
        return SyncJob(
            entity_id=row.id,
            connection_id=row.connection_id,
            job_type=row.job_type,
            state=row.state,
            cursor=SyncCursor.from_dict(dict(row.cursor or {})),
            imported_count=row.imported_count,
            last_error=row.last_error,
            created_at=ensure_utc(row.created_at) or row.created_at,
            updated_at=ensure_utc(row.updated_at),
        )

    async def get(self, job_id: uuid.UUID) -> SyncJob | None:
        row = await self._session.get(orm.SyncJobRow, job_id)
        return self._job(row) if row else None

    async def list_for_connection(self, connection_id: uuid.UUID) -> list[SyncJob]:
        rows = (
            (
                await self._session.execute(
                    sa.select(orm.SyncJobRow)
                    .where(orm.SyncJobRow.connection_id == connection_id)
                    .order_by(orm.SyncJobRow.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        return [self._job(row) for row in rows]

    async def add(self, job: SyncJob) -> None:
        self._session.add(
            orm.SyncJobRow(
                id=job.id,
                connection_id=job.connection_id,
                job_type=job.job_type,
                state=job.state,
                cursor=job.cursor.to_dict(),
                imported_count=job.imported_count,
                last_error=job.last_error,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
        )
        await self._session.flush()

    async def save(self, job: SyncJob) -> None:
        row = await self._session.get(orm.SyncJobRow, job.id)
        if row is None:
            await self.add(job)
            return
        row.state = job.state
        row.cursor = job.cursor.to_dict()
        row.imported_count = job.imported_count
        row.last_error = job.last_error
        row.updated_at = job.updated_at
        await self._session.flush()


class SqlExternalMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(
        self, connection_id: uuid.UUID, entity_type: str, external_id: str
    ) -> uuid.UUID | None:
        row = (
            await self._session.execute(
                sa.select(orm.ExternalMappingRow).where(
                    orm.ExternalMappingRow.connection_id == connection_id,
                    orm.ExternalMappingRow.entity_type == entity_type,
                    orm.ExternalMappingRow.external_id == external_id,
                )
            )
        ).scalar_one_or_none()
        return row.internal_id if row else None

    async def save(
        self,
        connection_id: uuid.UUID,
        entity_type: str,
        external_id: str,
        internal_id: uuid.UUID,
        field_map: dict[str, str] | None = None,
    ) -> None:
        existing = await self.find(connection_id, entity_type, external_id)
        if existing is not None:
            return
        self._session.add(
            orm.ExternalMappingRow(
                id=uuid.uuid4(),
                connection_id=connection_id,
                entity_type=entity_type,
                external_id=external_id,
                internal_id=internal_id,
                field_map=field_map or {},
                created_at=datetime.now(tz=None).astimezone(),
            )
        )
        await self._session.flush()

    async def list_by_type(
        self, connection_id: uuid.UUID, entity_type: str
    ) -> list[tuple[str, uuid.UUID]]:
        rows = (
            (
                await self._session.execute(
                    sa.select(orm.ExternalMappingRow).where(
                        orm.ExternalMappingRow.connection_id == connection_id,
                        orm.ExternalMappingRow.entity_type == entity_type,
                    )
                )
            )
            .scalars()
            .all()
        )
        return [(row.external_id, row.internal_id) for row in rows]

    async def delete_for_connection(self, connection_id: uuid.UUID) -> None:
        await self._session.execute(
            sa.delete(orm.ExternalMappingRow).where(
                orm.ExternalMappingRow.connection_id == connection_id
            )
        )
        await self._session.flush()


class SqlWebhookEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(
        self, connection_id: uuid.UUID, external_event_id: str, received_at: datetime
    ) -> bool:
        try:
            async with self._session.begin_nested():
                self._session.add(
                    orm.WebhookEventRow(
                        id=uuid.uuid4(),
                        connection_id=connection_id,
                        external_event_id=external_event_id,
                        received_at=received_at,
                    )
                )
            return True
        except IntegrityError:
            return False
