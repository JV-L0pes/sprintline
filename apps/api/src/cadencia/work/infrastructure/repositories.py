"""Adaptadores SQLAlchemy das portas de work."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from cadencia.platform.db import ensure_utc
from cadencia.platform.events import audit_for, clock_for, recorder_for
from cadencia.work.domain.entities import Board, BoardColumn, Project, Sprint, WorkItem
from cadencia.work.domain.repositories import AssignmentRecord
from cadencia.work.domain.value_objects import (
    Priority,
    ProjectMode,
    SprintState,
    StatusCategory,
    WipEnforcement,
    WorkItemType,
)
from cadencia.work.infrastructure import orm


def _project(row: orm.ProjectRow) -> Project:
    return Project(
        entity_id=row.id,
        workspace_id=row.workspace_id,
        name=row.name,
        key=row.key,
        mode=ProjectMode(row.mode),
        wip_enforcement=WipEnforcement(row.wip_enforcement),
        next_number=row.next_number,
        created_at=ensure_utc(row.created_at) or row.created_at,
        archived_at=ensure_utc(row.archived_at),
    )


def _column(row: orm.BoardColumnRow) -> BoardColumn:
    return BoardColumn(
        entity_id=row.id,
        board_id=row.board_id,
        name=row.name,
        position=row.position,
        category=StatusCategory(row.category),
        wip_limit=row.wip_limit,
    )


def _board(row: orm.BoardRow, columns: list[orm.BoardColumnRow]) -> Board:
    return Board(
        entity_id=row.id,
        project_id=row.project_id,
        name=row.name,
        columns=[_column(column) for column in columns],
    )


def _sprint(row: orm.SprintRow) -> Sprint:
    return Sprint(
        entity_id=row.id,
        board_id=row.board_id,
        name=row.name,
        goal=row.goal,
        state=SprintState(row.state),
        start_date=row.start_date,
        end_date=row.end_date,
        created_at=ensure_utc(row.created_at) or row.created_at,
        completed_at=ensure_utc(row.completed_at),
    )


async def _workspace_for_project(session: AsyncSession, project_id: uuid.UUID) -> uuid.UUID | None:
    return (
        await session.execute(
            sa.select(orm.ProjectRow.workspace_id).where(orm.ProjectRow.id == project_id)
        )
    ).scalar_one_or_none()


async def _workspace_for_board(session: AsyncSession, board_id: uuid.UUID) -> uuid.UUID | None:
    return (
        await session.execute(
            sa.select(orm.ProjectRow.workspace_id)
            .join(orm.BoardRow, orm.BoardRow.project_id == orm.ProjectRow.id)
            .where(orm.BoardRow.id == board_id)
        )
    ).scalar_one_or_none()


def _item(row: orm.WorkItemRow) -> WorkItem:
    return WorkItem(
        entity_id=row.id,
        project_id=row.project_id,
        parent_id=row.parent_id,
        sprint_id=row.sprint_id,
        key=row.key,
        type=WorkItemType(row.type),
        title=row.title,
        description=row.description,
        status_column_id=row.status_column_id,
        story_points=row.story_points,
        priority=Priority(row.priority),
        assignee_id=row.assignee_id,
        position=row.position,
        due_date=row.due_date,
        created_at=ensure_utc(row.created_at) or row.created_at,
        updated_at=ensure_utc(row.updated_at),
        done_at=ensure_utc(row.done_at),
        first_in_progress_at=ensure_utc(row.first_in_progress_at),
        archived_at=ensure_utc(row.archived_at),
        version=row.version,
    )


class SqlProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, project_id: uuid.UUID, workspace_id: uuid.UUID) -> Project | None:
        row = (
            await self._session.execute(
                sa.select(orm.ProjectRow).where(
                    orm.ProjectRow.id == project_id,
                    orm.ProjectRow.workspace_id == workspace_id,
                    orm.ProjectRow.archived_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        return _project(row) if row else None

    async def list_for_workspace(self, workspace_id: uuid.UUID) -> list[Project]:
        rows = (
            (
                await self._session.execute(
                    sa.select(orm.ProjectRow)
                    .where(
                        orm.ProjectRow.workspace_id == workspace_id,
                        orm.ProjectRow.archived_at.is_(None),
                    )
                    .order_by(orm.ProjectRow.created_at)
                )
            )
            .scalars()
            .all()
        )
        return [_project(row) for row in rows]

    async def key_exists(
        self,
        workspace_id: uuid.UUID,
        key: str,
        *,
        exclude_project_id: uuid.UUID | None = None,
    ) -> bool:
        query = (
            sa.select(sa.func.count())
            .select_from(orm.ProjectRow)
            .where(
                orm.ProjectRow.workspace_id == workspace_id,
                orm.ProjectRow.key == key,
            )
        )
        if exclude_project_id is not None:
            query = query.where(orm.ProjectRow.id != exclude_project_id)
        return bool((await self._session.execute(query)).scalar_one())

    def _append_events(self, project: Project) -> None:
        recorder_for(self._session).append(
            project,
            workspace_id=project.workspace_id,
            audit=audit_for(self._session),
            occurred_at=clock_for(self._session).now(),
        )

    async def add(self, project: Project) -> None:
        self._session.add(
            orm.ProjectRow(
                id=project.id,
                workspace_id=project.workspace_id,
                name=project.name,
                key=project.key,
                mode=project.mode.value,
                wip_enforcement=project.wip_enforcement.value,
                next_number=project.next_number,
                created_at=project.created_at,
                archived_at=project.archived_at,
            )
        )
        await self._session.flush()
        self._append_events(project)

    async def save(self, project: Project) -> None:
        row = await self._session.get(orm.ProjectRow, project.id)
        if row is None:
            await self.add(project)
            return
        row.name = project.name
        row.next_number = project.next_number
        row.mode = project.mode.value
        row.wip_enforcement = project.wip_enforcement.value
        row.archived_at = project.archived_at
        await self._session.flush()
        self._append_events(project)


class SqlBoardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _assemble(self, row: orm.BoardRow | None) -> Board | None:
        if row is None:
            return None
        columns = (
            (
                await self._session.execute(
                    sa.select(orm.BoardColumnRow)
                    .where(orm.BoardColumnRow.board_id == row.id)
                    .order_by(orm.BoardColumnRow.position)
                )
            )
            .scalars()
            .all()
        )
        return _board(row, list(columns))

    async def get(self, board_id: uuid.UUID) -> Board | None:
        return await self._assemble(await self._session.get(orm.BoardRow, board_id))

    async def get_by_project(self, project_id: uuid.UUID) -> Board | None:
        row = (
            await self._session.execute(
                sa.select(orm.BoardRow).where(orm.BoardRow.project_id == project_id)
            )
        ).scalar_one_or_none()
        return await self._assemble(row)

    async def add(self, board: Board) -> None:
        self._session.add(orm.BoardRow(id=board.id, project_id=board.project_id, name=board.name))
        # Postgres valida FK de imediato: garante o board antes das colunas
        # (o ordenamento do flush não e garantido sem relationship()).
        await self._session.flush()
        for column in board.columns:
            self._session.add(
                orm.BoardColumnRow(
                    id=column.id,
                    board_id=board.id,
                    name=column.name,
                    position=column.position,
                    category=column.category.value,
                    wip_limit=column.wip_limit,
                )
            )
        await self._session.flush()

    async def save(self, board: Board) -> None:
        row = await self._session.get(orm.BoardRow, board.id)
        if row is None:
            await self.add(board)
            return
        row.name = board.name
        existing = {
            column_row.id: column_row
            for column_row in (
                await self._session.execute(
                    sa.select(orm.BoardColumnRow).where(orm.BoardColumnRow.board_id == board.id)
                )
            )
            .scalars()
            .all()
        }
        kept_ids = {column.id for column in board.columns}
        for column in board.columns:
            column_row = existing.get(column.id)
            if column_row is None:
                self._session.add(
                    orm.BoardColumnRow(
                        id=column.id,
                        board_id=board.id,
                        name=column.name,
                        position=column.position,
                        category=column.category.value,
                        wip_limit=column.wip_limit,
                    )
                )
            else:
                column_row.name = column.name
                column_row.position = column.position
                column_row.category = column.category.value
                column_row.wip_limit = column.wip_limit
        for column_id, column_row in existing.items():
            if column_id not in kept_ids:
                await self._session.delete(column_row)
        await self._session.flush()


class SqlWorkItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, item_id: uuid.UUID) -> WorkItem | None:
        row = await self._session.get(orm.WorkItemRow, item_id)
        return _item(row) if row else None

    async def get_by_key(self, project_id: uuid.UUID, key: str) -> WorkItem | None:
        row = (
            await self._session.execute(
                sa.select(orm.WorkItemRow).where(
                    orm.WorkItemRow.project_id == project_id, orm.WorkItemRow.key == key
                )
            )
        ).scalar_one_or_none()
        return _item(row) if row else None

    async def list_for_project(self, project_id: uuid.UUID) -> list[WorkItem]:
        rows = (
            (
                await self._session.execute(
                    sa.select(orm.WorkItemRow)
                    .where(
                        orm.WorkItemRow.project_id == project_id,
                        orm.WorkItemRow.archived_at.is_(None),
                    )
                    .order_by(orm.WorkItemRow.position, orm.WorkItemRow.created_at)
                )
            )
            .scalars()
            .all()
        )
        return [_item(row) for row in rows]

    async def list_for_sprint(self, sprint_id: uuid.UUID) -> list[WorkItem]:
        rows = (
            (
                await self._session.execute(
                    sa.select(orm.WorkItemRow)
                    .where(
                        orm.WorkItemRow.sprint_id == sprint_id,
                        orm.WorkItemRow.archived_at.is_(None),
                    )
                    .order_by(orm.WorkItemRow.position)
                )
            )
            .scalars()
            .all()
        )
        return [_item(row) for row in rows]

    async def list_in_column(self, column_id: uuid.UUID) -> list[WorkItem]:
        rows = (
            (
                await self._session.execute(
                    sa.select(orm.WorkItemRow)
                    .where(
                        orm.WorkItemRow.status_column_id == column_id,
                        orm.WorkItemRow.archived_at.is_(None),
                    )
                    .order_by(orm.WorkItemRow.position, orm.WorkItemRow.created_at)
                )
            )
            .scalars()
            .all()
        )
        return [_item(row) for row in rows]

    async def count_in_column(
        self, column_id: uuid.UUID, *, exclude_item_id: uuid.UUID | None = None
    ) -> int:
        query = (
            sa.select(sa.func.count())
            .select_from(orm.WorkItemRow)
            .where(
                orm.WorkItemRow.status_column_id == column_id,
                orm.WorkItemRow.archived_at.is_(None),
            )
        )
        if exclude_item_id is not None:
            query = query.where(orm.WorkItemRow.id != exclude_item_id)
        return int((await self._session.execute(query)).scalar_one())

    async def next_position(self, column_id: uuid.UUID) -> float:
        maximum = (
            await self._session.execute(
                sa.select(sa.func.max(orm.WorkItemRow.position)).where(
                    orm.WorkItemRow.status_column_id == column_id
                )
            )
        ).scalar_one()
        return float(maximum or 0.0) + 1.0

    async def _append_events(self, item: WorkItem) -> None:
        if not item.peek_events():
            return
        recorder_for(self._session).append(
            item,
            workspace_id=await _workspace_for_project(self._session, item.project_id),
            audit=audit_for(self._session),
            occurred_at=clock_for(self._session).now(),
        )

    async def add(self, item: WorkItem) -> None:
        self._session.add(self._to_row(item))
        await self._session.flush()
        await self._append_events(item)

    async def save(self, item: WorkItem) -> None:
        row = await self._session.get(orm.WorkItemRow, item.id)
        if row is None:
            await self.add(item)
            return
        self._apply(row, item)
        await self._session.flush()
        await self._append_events(item)

    async def save_many(self, items: list[WorkItem]) -> None:
        for item in items:
            await self.save(item)

    def _to_row(self, item: WorkItem) -> orm.WorkItemRow:
        row = orm.WorkItemRow(id=item.id, project_id=item.project_id)
        self._apply(row, item)
        row.created_at = item.created_at
        return row

    def _apply(self, row: orm.WorkItemRow, item: WorkItem) -> None:
        row.parent_id = item.parent_id
        row.sprint_id = item.sprint_id
        row.type = item.type.value
        row.key = item.key
        row.title = item.title
        row.description = item.description
        row.status_column_id = item.status_column_id
        row.story_points = item.story_points
        row.priority = item.priority.value
        row.assignee_id = item.assignee_id
        row.position = item.position
        row.due_date = item.due_date
        row.updated_at = item.updated_at
        row.done_at = item.done_at
        row.first_in_progress_at = item.first_in_progress_at
        row.archived_at = item.archived_at
        row.version = item.version


class SqlSprintRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, sprint_id: uuid.UUID) -> Sprint | None:
        row = await self._session.get(orm.SprintRow, sprint_id)
        return _sprint(row) if row else None

    async def list_for_project(self, project_id: uuid.UUID) -> list[Sprint]:
        rows = (
            (
                await self._session.execute(
                    sa.select(orm.SprintRow)
                    .join(orm.BoardRow, orm.BoardRow.id == orm.SprintRow.board_id)
                    .where(orm.BoardRow.project_id == project_id)
                    .order_by(orm.SprintRow.start_date)
                )
            )
            .scalars()
            .all()
        )
        return [_sprint(row) for row in rows]

    async def active_for_board(self, board_id: uuid.UUID) -> Sprint | None:
        row = (
            await self._session.execute(
                sa.select(orm.SprintRow).where(
                    orm.SprintRow.board_id == board_id,
                    orm.SprintRow.state == SprintState.ACTIVE.value,
                )
            )
        ).scalar_one_or_none()
        return _sprint(row) if row else None

    async def count_assigned(self, sprint_id: uuid.UUID) -> int:
        return int(
            (
                await self._session.execute(
                    sa.select(sa.func.count())
                    .select_from(orm.WorkItemRow)
                    .where(
                        orm.WorkItemRow.sprint_id == sprint_id,
                        orm.WorkItemRow.archived_at.is_(None),
                    )
                )
            ).scalar_one()
        )

    async def _append_events(self, sprint: Sprint) -> None:
        recorder_for(self._session).append(
            sprint,
            workspace_id=await _workspace_for_board(self._session, sprint.board_id),
            audit=audit_for(self._session),
            occurred_at=clock_for(self._session).now(),
        )

    async def add(self, sprint: Sprint) -> None:
        self._session.add(self._to_row(sprint))
        await self._session.flush()
        await self._append_events(sprint)

    async def save(self, sprint: Sprint) -> None:
        row = await self._session.get(orm.SprintRow, sprint.id)
        if row is None:
            await self.add(sprint)
            return
        row.name = sprint.name
        row.goal = sprint.goal
        row.state = sprint.state.value
        row.start_date = sprint.start_date
        row.end_date = sprint.end_date
        row.completed_at = sprint.completed_at
        await self._session.flush()
        await self._append_events(sprint)

    def _to_row(self, sprint: Sprint) -> orm.SprintRow:
        return orm.SprintRow(
            id=sprint.id,
            board_id=sprint.board_id,
            name=sprint.name,
            goal=sprint.goal,
            state=sprint.state.value,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            completed_at=sprint.completed_at,
            created_at=sprint.created_at,
        )


class SqlAssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: AssignmentRecord) -> None:
        self._session.add(
            orm.SprintAssignmentRow(
                id=record.id,
                work_item_id=record.work_item_id,
                sprint_id=record.sprint_id,
                added_at=record.added_at,
                removed_at=record.removed_at,
            )
        )
        await self._session.flush()

    async def close_open_for_item(self, item_id: uuid.UUID, now: datetime) -> None:
        await self._session.execute(
            sa.update(orm.SprintAssignmentRow)
            .where(
                orm.SprintAssignmentRow.work_item_id == item_id,
                orm.SprintAssignmentRow.removed_at.is_(None),
            )
            .values(removed_at=now)
        )
        await self._session.flush()

    async def list_for_sprint(self, sprint_id: uuid.UUID) -> list[AssignmentRecord]:
        rows = (
            (
                await self._session.execute(
                    sa.select(orm.SprintAssignmentRow)
                    .where(orm.SprintAssignmentRow.sprint_id == sprint_id)
                    .order_by(orm.SprintAssignmentRow.added_at)
                )
            )
            .scalars()
            .all()
        )
        return [
            AssignmentRecord(
                id=row.id,
                work_item_id=row.work_item_id,
                sprint_id=row.sprint_id,
                added_at=ensure_utc(row.added_at) or row.added_at,
                removed_at=ensure_utc(row.removed_at),
            )
            for row in rows
        ]

    async def list_for_item(self, item_id: uuid.UUID) -> list[AssignmentRecord]:
        rows = (
            (
                await self._session.execute(
                    sa.select(orm.SprintAssignmentRow)
                    .where(orm.SprintAssignmentRow.work_item_id == item_id)
                    .order_by(orm.SprintAssignmentRow.added_at)
                )
            )
            .scalars()
            .all()
        )
        return [
            AssignmentRecord(
                id=row.id,
                work_item_id=row.work_item_id,
                sprint_id=row.sprint_id,
                added_at=ensure_utc(row.added_at) or row.added_at,
                removed_at=ensure_utc(row.removed_at),
            )
            for row in rows
        ]
