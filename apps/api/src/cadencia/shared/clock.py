"""Relogio injetavel — dominio e casos de uso nunca chamam datetime.now() diretamente."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """Relogio de producao: sempre UTC aware."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FrozenClock:
    """Relogio deterministico para testes e seeds; avancavel manualmente."""

    def __init__(self, current: datetime) -> None:
        if current.tzinfo is None:
            raise ValueError("FrozenClock exige datetime com timezone")
        self._current = current.astimezone(UTC)

    def now(self) -> datetime:
        return self._current

    def set(self, moment: datetime) -> None:
        self._current = moment.astimezone(UTC)

    def advance(self, **delta: float) -> None:
        from datetime import timedelta

        self._current = self._current + timedelta(**delta)
