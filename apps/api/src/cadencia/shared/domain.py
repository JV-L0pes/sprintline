"""Kernel do dominio: entidades, agregados, eventos e objetos de valor."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, ClassVar
from uuid import UUID

from cadencia.shared.ids import uuid7


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Evento imutável. Subclasses declaram `event_type` e campos de payload."""

    event_type: ClassVar[str] = ""

    def payload(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for spec in fields(self):
            value = getattr(self, spec.name)
            data[spec.name] = _serialize(value)
        return data


def _serialize(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, tuple | list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class ValueObject:
    """Marcador semântico para objetos de valor (sempre imutáveis)."""


class Entity:
    def __init__(self, entity_id: UUID | None = None) -> None:
        self.id: UUID = entity_id or uuid7()
        self._events: list[DomainEvent] = []

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    def peek_events(self) -> list[DomainEvent]:
        return list(self._events)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Entity) and other.id == self.id and type(other) is type(self)

    def __hash__(self) -> int:
        return hash((type(self), self.id))


class AggregateRoot(Entity):
    """Raiz de agregado: única porta de escrita e de levantamento de eventos."""


@dataclass
class AuditInfo:
    """Metadados de auditoria carregados pelo caso de uso a partir do ator."""

    actor_id: UUID | None = None
    source: str = "local"


def paginate(items: list[Any], limit: int, offset: int) -> tuple[list[Any], bool]:
    window = items[offset : offset + limit]
    has_more = len(items) > offset + limit
    return window, has_more


__all__ = [
    "AggregateRoot",
    "AuditInfo",
    "DomainEvent",
    "Entity",
    "ValueObject",
    "paginate",
]
