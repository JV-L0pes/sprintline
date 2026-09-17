"""Testes de dominio do contexto work (RN-05..RN-18)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from cadencia.shared.errors import ConflictError, ValidationError
from cadencia.work.domain.entities import Board, BoardColumn, Project, Sprint, WorkItem
from cadencia.work.domain.policies import WipVerdict, wip_verdict
from cadencia.work.domain.value_objects import (
    Priority,
    ProjectMode,
    SprintState,
    StatusCategory,
    WorkItemType,
)

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def make_project(**overrides: object) -> Project:
    defaults = {
        "workspace_id": uuid.uuid4(),
        "name": "App",
        "key": "APP",
        "mode": ProjectMode.POINTS,
        "wip_enforcement": "SOFT",
        "now": NOW,
    }
    return Project.create(**{**defaults, **overrides})  # type: ignore[arg-type]


def make_board(project_id: uuid.UUID) -> Board:
    return Board.with_default_columns(project_id=project_id, name="Board")


def make_item(
    project: Project,
    board: Board,
    *,
    item_type: WorkItemType = WorkItemType.STORY,
    points: int | None = 3,
    parent_id: uuid.UUID | None = None,
    parent_type: WorkItemType | None = None,
) -> WorkItem:
    return WorkItem.create(
        project=project,
        item_type=item_type,
        title="Titulo",
        todo_column_id=board.first_todo_column().id,
        position=1.0,
        parent_id=parent_id,
        parent_type=parent_type,
        story_points=points,
        key="APP-1",
        now=NOW,
    )


def test_project_key_normalization_and_validation() -> None:
    assert make_project(key="app").key == "APP"
    with pytest.raises(ValidationError):
        make_project(key="1")
    with pytest.raises(ValidationError):
        make_project(key="chave-muito-longa")


def test_hierarchy_rules() -> None:
    project = make_project()
    board = make_board(project.id)
    epic = make_item(project, board, item_type=WorkItemType.EPIC, points=8)

    with pytest.raises(ValidationError):
        make_item(
            project,
            board,
            item_type=WorkItemType.EPIC,
            parent_id=epic.id,
            parent_type=WorkItemType.EPIC,
        )
    with pytest.raises(ValidationError):
        make_item(
            project,
            board,
            item_type=WorkItemType.SUBTASK,
            points=None,
            parent_id=epic.id,
            parent_type=WorkItemType.EPIC,
        )


def test_story_points_fibonacci_validation() -> None:
    project = make_project()
    board = make_board(project.id)
    assert make_item(project, board, points=5).story_points == 5
    with pytest.raises(ValidationError):
        make_item(project, board, points=4)


def test_subtask_cannot_have_points() -> None:
    project = make_project()
    board = make_board(project.id)
    with pytest.raises(ValidationError):
        make_item(project, board, item_type=WorkItemType.SUBTASK, points=3)


def test_sprint_duration_limits() -> None:
    board_id = uuid.uuid4()
    with pytest.raises(ValidationError):
        Sprint.create(
            board_id=board_id,
            name="Curta",
            goal="g",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 5),
            now=NOW,
        )
    with pytest.raises(ValidationError):
        Sprint.create(
            board_id=board_id,
            name="Longa",
            goal="g",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 10, 15),
            now=NOW,
        )
    sprint = Sprint.create(
        board_id=board_id,
        name="OK",
        goal="g",
        start_date=date(2026, 9, 7),
        end_date=date(2026, 9, 20),
        now=NOW,
    )
    assert sprint.state is SprintState.PLANNED


def test_sprint_start_requirements() -> None:
    board_id = uuid.uuid4()
    sprint = Sprint.create(
        board_id=board_id,
        name="S1",
        goal=None,
        start_date=date(2026, 9, 7),
        end_date=date(2026, 9, 20),
        now=NOW,
    )
    with pytest.raises(ValidationError):
        sprint.start(assigned_items=3)
    sprint.update_plan(name=None, goal="Entregar login")
    with pytest.raises(ValidationError):
        sprint.start(assigned_items=0)
    sprint.start(assigned_items=2)
    assert sprint.state is SprintState.ACTIVE
    with pytest.raises(ConflictError):
        sprint.start(assigned_items=2)


def test_sprint_complete_only_when_active() -> None:
    sprint = Sprint.create(
        board_id=uuid.uuid4(),
        name="S1",
        goal="g",
        start_date=date(2026, 9, 7),
        end_date=date(2026, 9, 20),
        now=NOW,
    )
    with pytest.raises(ConflictError):
        sprint.complete(now=NOW)
    sprint.start(assigned_items=1)
    sprint.complete(now=NOW)
    assert sprint.state is SprintState.COMPLETED
    assert sprint.completed_at == NOW
    with pytest.raises(ConflictError):
        sprint.update_plan(name="x", goal="y")


def test_work_item_lifecycle_sets_timestamps_and_events() -> None:
    project = make_project()
    board = make_board(project.id)
    item = make_item(project, board)
    item.pull_events()

    in_progress = _column(board, StatusCategory.IN_PROGRESS)
    item.move_to(column=in_progress, now=NOW)
    assert item.first_in_progress_at == NOW
    assert item.done_at is None
    types = [event.event_type for event in item.pull_events()]
    assert types == ["work_item.moved"]

    done = _column(board, StatusCategory.DONE)
    item.move_to(column=done, now=NOW)
    assert item.done_at == NOW
    types = [event.event_type for event in item.pull_events()]
    assert types == ["work_item.completed", "work_item.moved"]

    item.move_to(column=board.first_todo_column(), now=NOW)
    assert item.done_at is None
    assert item.first_in_progress_at == NOW  # nunca e limpo (cycle time historico)
    types = [event.event_type for event in item.pull_events()]
    assert types == ["work_item.reopened", "work_item.moved"]


def test_work_item_sprint_assignment_records_event() -> None:
    project = make_project()
    board = make_board(project.id)
    item = make_item(project, board)
    item.pull_events()
    sprint_id = uuid.uuid4()
    item.assign_sprint(sprint_id, now=NOW)
    assert item.sprint_id == sprint_id
    events = item.pull_events()
    assert events[0].event_type == "work_item.sprint_changed"
    item.assign_sprint(None, now=NOW)
    assert item.sprint_id is None


def test_wip_verdict() -> None:
    assert wip_verdict(wip_limit=None, current_count=99, enforcement="HARD") == WipVerdict.OK
    assert wip_verdict(wip_limit=3, current_count=2, enforcement="HARD") == WipVerdict.OK
    assert wip_verdict(wip_limit=3, current_count=3, enforcement="SOFT") == WipVerdict.WARN
    assert wip_verdict(wip_limit=3, current_count=3, enforcement="HARD") == WipVerdict.BLOCK


def test_item_archive_is_idempotent_guard() -> None:
    project = make_project()
    board = make_board(project.id)
    item = make_item(project, board)
    item.archive(now=NOW)
    assert item.archived_at == NOW
    with pytest.raises(ConflictError):
        item.archive(now=NOW)


def _column(board: Board, category: StatusCategory) -> BoardColumn:
    return next(column for column in board.columns if column.category is category)


def test_default_board_columns_cover_all_categories() -> None:
    board = make_board(uuid.uuid4())
    categories = {column.category for column in board.columns}
    assert categories == {StatusCategory.TODO, StatusCategory.IN_PROGRESS, StatusCategory.DONE}


def test_priority_validation() -> None:
    project = make_project()
    board = make_board(project.id)
    item = make_item(project, board)
    item.update_details(now=NOW, priority=Priority.HIGHEST)
    assert item.priority is Priority.HIGHEST
