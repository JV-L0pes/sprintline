"""Append de eventos de dominio no event log (mesma transacao do agregado).

O recorder vive em `session.info`, então os repositórios persistem eventos sem
que casos de uso precisem de plumbing manual — a invariante "toda escrita de
agregado gera evento" (RN-23) fica garantida em um único lugar.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from cadencia.platform.orm import DomainEventRow
from cadencia.shared.clock import Clock, SystemClock
from cadencia.shared.domain import AggregateRoot, AuditInfo, DomainEvent


class EventRecorder:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def append(
        self,
        aggregate: AggregateRoot,
        *,
        workspace_id: uuid.UUID | None,
        audit: AuditInfo,
        occurred_at: datetime | None = None,
        source: str | None = None,
        external_event_id: str | None = None,
    ) -> None:
        moment = occurred_at or self._clock.now()
        for event in aggregate.pull_events():
            self.append_raw(
                event,
                aggregate_type=type(aggregate).__name__.lower(),
                aggregate_id=aggregate.id,
                workspace_id=workspace_id,
                audit=audit,
                occurred_at=moment,
                source=source,
                external_event_id=external_event_id,
            )

    def append_raw(
        self,
        event: DomainEvent,
        *,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        workspace_id: uuid.UUID | None,
        audit: AuditInfo,
        occurred_at: datetime | None = None,
        source: str | None = None,
        external_event_id: str | None = None,
    ) -> None:
        moment = occurred_at or self._clock.now()
        self._session.add(
            DomainEventRow(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                type=event.event_type,
                payload=event.payload(),
                actor_id=audit.actor_id,
                source=source or audit.source,
                external_event_id=external_event_id,
                occurred_at=moment,
                recorded_at=moment,
            )
        )


def recorder_for(session: AsyncSession) -> EventRecorder:
    recorder = session.info.get("event_recorder")
    if recorder is None:
        recorder = EventRecorder(session, session.info.get("clock") or SystemClock())
        session.info["event_recorder"] = recorder
    return recorder


def clock_for(session: AsyncSession) -> Clock:
    return session.info.get("clock") or SystemClock()


def audit_for(session: AsyncSession) -> AuditInfo:
    audit = session.info.get("audit")
    return audit if isinstance(audit, AuditInfo) else AuditInfo()
