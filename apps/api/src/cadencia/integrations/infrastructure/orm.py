"""Mapeamento relacional do contexto integrations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from cadencia.platform.db import Base, JSONVariant


class IntegrationRow(Base):
    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(sa.String(16))
    cloud_id: Mapped[str] = mapped_column(sa.String(80))
    site_url: Mapped[str] = mapped_column(sa.String(255))
    status: Mapped[str] = mapped_column(sa.String(16), default="CONNECTED")
    field_map: Mapped[dict[str, str]] = mapped_column(JSONVariant, default=dict)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))


class IntegrationTokenRow(Base):
    __tablename__ = "integration_tokens"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("integrations.id", ondelete="CASCADE"), unique=True
    )
    access_token_enc: Mapped[str] = mapped_column(sa.Text)
    refresh_token_enc: Mapped[str] = mapped_column(sa.Text)
    access_expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))


class ExternalMappingRow(Base):
    __tablename__ = "external_mappings"
    __table_args__ = (
        sa.UniqueConstraint(
            "connection_id", "entity_type", "external_id", name="uq_external_mappings_key"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("integrations.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[str] = mapped_column(sa.String(24))
    external_id: Mapped[str] = mapped_column(sa.String(80))
    internal_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True))
    field_map: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))


class SyncJobRow(Base):
    __tablename__ = "sync_jobs"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("integrations.id", ondelete="CASCADE"), index=True
    )
    job_type: Mapped[str] = mapped_column(sa.String(32))
    state: Mapped[str] = mapped_column(sa.String(16), default="PENDING")
    cursor: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict)
    imported_count: Mapped[int] = mapped_column(sa.Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(sa.String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), default=None)


class WebhookEventRow(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        sa.UniqueConstraint("connection_id", "external_event_id", name="uq_webhook_events_dedupe"),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("integrations.id", ondelete="CASCADE"), index=True
    )
    external_event_id: Mapped[str] = mapped_column(sa.String(200))
    received_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
