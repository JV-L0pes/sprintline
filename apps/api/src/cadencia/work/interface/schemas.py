"""Schemas HTTP do contexto work."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from cadencia.work.domain.value_objects import (
    Priority,
    ProjectMode,
    SprintState,
    StatusCategory,
    WipEnforcement,
    WorkItemType,
)


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    key: str = Field(min_length=2, max_length=10)
    mode: ProjectMode = ProjectMode.POINTS
    wip_enforcement: WipEnforcement = WipEnforcement.SOFT


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key: str
    mode: ProjectMode
    wip_enforcement: WipEnforcement
    created_at: datetime


class ColumnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    position: int
    category: StatusCategory
    wip_limit: int | None
    item_count: int


class WorkItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class BoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    columns: list[ColumnOut]
    items: list[WorkItemOut]


class WorkItemCreateRequest(BaseModel):
    type: WorkItemType
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    priority: Priority = Priority.MEDIUM
    story_points: int | None = None
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None
    parent_id: uuid.UUID | None = None


class WorkItemUpdateRequest(BaseModel):
    expected_version: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: Priority | None = None
    assignee_id: uuid.UUID | None = None
    clear_assignee: bool = False
    story_points: int | None = None
    clear_points: bool = False
    due_date: date | None = None
    clear_due_date: bool = False


class WorkItemMoveRequest(BaseModel):
    column_id: uuid.UUID
    index: int = Field(ge=0)
    expected_version: int | None = None


class WorkItemMoveResponse(BaseModel):
    item: WorkItemOut
    wip_warning: bool


class AssignSprintRequest(BaseModel):
    sprint_id: uuid.UUID | None = None


class SprintCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    goal: str | None = Field(default=None, max_length=280)
    start_date: date
    end_date: date


class SprintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class CompleteSprintRequest(BaseModel):
    target_sprint_id: uuid.UUID | None = None


class ColumnCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    category: StatusCategory
    wip_limit: int | None = Field(default=None, ge=1)


class ColumnUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    wip_limit: int | None = Field(default=None, ge=1)
    clear_wip: bool = False


class ColumnOrderRequest(BaseModel):
    column_ids: list[uuid.UUID] = Field(min_length=1)
