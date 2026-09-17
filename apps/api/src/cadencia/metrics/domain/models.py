"""Read models de métricas (RM-01..RM-15)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from cadencia.work.domain.value_objects import ProjectMode, StatusCategory


@dataclass(frozen=True)
class ItemFlowEvent:
    occurred_at: datetime
    category: StatusCategory


@dataclass(frozen=True)
class AssignmentWindow:
    added_at: datetime
    removed_at: datetime | None = None


@dataclass(frozen=True)
class ItemFlow:
    """Item com sua história completa de escopo e status (event sourcing, RN-23)."""

    id: uuid.UUID
    key: str
    story_points: int | None
    is_subtask: bool
    created_at: datetime
    windows: tuple[AssignmentWindow, ...] = ()
    category_events: tuple[ItemFlowEvent, ...] = ()

    def weight(self, mode: ProjectMode) -> float:
        if mode is ProjectMode.COUNT:
            return 1.0
        if self.is_subtask or self.story_points is None:
            return 0.0
        return float(self.story_points)

    def counted_in_points(self, mode: ProjectMode) -> bool:
        return mode is ProjectMode.POINTS and not self.is_subtask and self.story_points is not None

    def in_scope_at(self, moment: datetime) -> bool:
        return any(
            window.added_at <= moment and (window.removed_at is None or window.removed_at > moment)
            for window in self.windows
        )

    def category_at(self, moment: datetime) -> StatusCategory | None:
        current: StatusCategory | None = None
        for event in self.category_events:
            if event.occurred_at <= moment:
                current = event.category
            else:
                break
        return current


@dataclass(frozen=True)
class ScopeChange:
    date: date
    delta: float
    kind: str  # "added" | "removed"


@dataclass(frozen=True)
class DayPoint:
    date: date
    index: int
    ideal: float
    remaining: float
    completed: float
    scope: float


@dataclass(frozen=True)
class BurndownTotals:
    initial_scope: float
    final_scope: float
    completed: float
    unestimated_items: int


@dataclass(frozen=True)
class BurndownSeries:
    sprint_id: uuid.UUID
    sprint_name: str
    unit: str
    start_date: date
    end_date: date
    days: list[DayPoint]
    scope_changes: list[ScopeChange]
    totals: BurndownTotals


@dataclass(frozen=True)
class SprintRef:
    id: uuid.UUID
    project_id: uuid.UUID
    board_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    timezone: str
    working_days: tuple[int, ...]
    mode: ProjectMode


@dataclass(frozen=True)
class SprintMetricsData:
    sprint: SprintRef
    items: list[ItemFlow]


@dataclass(frozen=True)
class VelocityPoint:
    sprint_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    committed: float
    completed: float
    added: float
    removed: float


@dataclass(frozen=True)
class VelocityReport:
    unit: str
    sprints: list[VelocityPoint]
    average: float


@dataclass(frozen=True)
class CfdDay:
    date: date
    counts: dict[str, int]


@dataclass(frozen=True)
class CfdSeries:
    sprint_id: uuid.UUID
    start_date: date
    end_date: date
    days: list[CfdDay] = field(default_factory=list)


@dataclass(frozen=True)
class FlowSnapshot:
    key: str
    created_at: datetime
    first_in_progress_at: datetime | None
    done_at: datetime


@dataclass(frozen=True)
class FlowTimes:
    count: int
    unit: str
    cycle_p50: float | None
    cycle_p85: float | None
    cycle_p95: float | None
    lead_p50: float | None
    lead_p85: float | None
    lead_p95: float | None
