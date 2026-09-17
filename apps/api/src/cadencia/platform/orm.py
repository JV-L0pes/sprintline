"""Tabelas transversais: event log append-only."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from cadencia.platform.db import Base, JSONVariant


class RateLimitHitRow(Base):
    """Contador de tentativas por chave/janela (rate limit do auth)."""

    __tablename__ = "rate_limit_hits"

    key: Mapped[str] = mapped_column(sa.String(255), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    count: Mapped[int] = mapped_column(sa.Integer, default=1)


class DomainEventRow(Base):
    """Fonte de verdade para métricas e auditoria. Nunca sofre UPDATE/DELETE (RN-25)."""

    __tablename__ = "domain_events"
    __table_args__ = (
        sa.UniqueConstraint(
            "source",
            "external_event_id",
            name="uq_domain_events_source_external",
        ),
        sa.Index("ix_domain_events_aggregate", "aggregate_type", "aggregate_id", "occurred_at"),
        sa.Index("ix_domain_events_workspace_occurred", "workspace_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid(as_uuid=True), nullable=True)
    aggregate_type: Mapped[str] = mapped_column(sa.String(64))
    aggregate_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True))
    type: Mapped[str] = mapped_column(sa.String(80))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid(as_uuid=True), nullable=True)
    source: Mapped[str] = mapped_column(sa.String(16), default="local")
    external_event_id: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
