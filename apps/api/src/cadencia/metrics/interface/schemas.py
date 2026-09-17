"""Schemas HTTP de métricas."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class DayPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    index: int
    ideal: float
    remaining: float
    completed: float
    scope: float


class ScopeChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    delta: float
    kind: str


class BurndownTotalsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    initial_scope: float
    final_scope: float
    completed: float
    unestimated_items: int


class BurndownOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sprint_id: uuid.UUID
    sprint_name: str
    unit: str
    start_date: date
    end_date: date
    days: list[DayPointOut]
    scope_changes: list[ScopeChangeOut]
    totals: BurndownTotalsOut


class CfdDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    counts: dict[str, int]


class CfdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sprint_id: uuid.UUID
    start_date: date
    end_date: date
    days: list[CfdDayOut]


class VelocityPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sprint_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    committed: float
    completed: float
    added: float
    removed: float


class VelocityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unit: str
    average: float
    sprints: list[VelocityPointOut]


class FlowTimesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    count: int
    unit: str
    cycle_p50: float | None
    cycle_p85: float | None
    cycle_p95: float | None
    lead_p50: float | None
    lead_p85: float | None
    lead_p95: float | None
