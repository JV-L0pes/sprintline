"""View models do contexto work."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from cadencia.work.domain.value_objects import (
    Priority,
    ProjectMode,
    SprintState,
    StatusCategory,
    WipEnforcement,
    WorkItemType,
)


@dataclass(frozen=True)
class ProjectView:
    id: uuid.UUID
    name: str
    key: str
    mode: ProjectMode
    wip_enforcement: WipEnforcement
    created_at: datetime


@dataclass(frozen=True)
class ColumnView:
    id: uuid.UUID
    name: str
    position: int
    category: StatusCategory
    wip_limit: int | None
    item_count: int


@dataclass(frozen=True)
class WorkItemView:
    id: uuid.UUID
    project_id: uuid.UUID
    key: str
    type: WorkItemType
    title: str
    description: str
    parent_id: uuid.UUID | None
    status_column_id: uuid.UUID
    status_category: StatusCategory
    story_points: int | None
    priority: Priority
    assignee_id: uuid.UUID | None
    sprint_id: uuid.UUID | None
    position: float
    due_date: date | None
    created_at: datetime
    updated_at: datetime | None
    done_at: datetime | None
    first_in_progress_at: datetime | None
    version: int


@dataclass(frozen=True)
class BoardView:
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    columns: list[ColumnView]
    items: list[WorkItemView] = field(default_factory=list)


@dataclass(frozen=True)
class SprintView:
    id: uuid.UUID
    board_id: uuid.UUID
    name: str
    goal: str | None
    state: SprintState
    start_date: date
    end_date: date
    completed_at: datetime | None
    total_items: int
    done_items: int
    total_points: int
    done_points: int


@dataclass(frozen=True)
class MoveResult:
    item: WorkItemView
    wip_warning: bool
