"""Leitura SQL do event log + trabalho para alimentar as calculadoras puras."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from cadencia.identity.infrastructure.orm import WorkspaceRow
from cadencia.metrics.domain.models import (
    AssignmentWindow,
    FlowSnapshot,
    ItemFlow,
    ItemFlowEvent,
    SprintMetricsData,
    SprintRef,
)
from cadencia.platform.db import ensure_utc
from cadencia.platform.orm import DomainEventRow
from cadencia.work.domain.value_objects import ProjectMode, StatusCategory, WorkItemType
from cadencia.work.infrastructure import orm as work_orm

_CATEGORY_EVENT_TYPES = ("work_item.created", "work_item.moved")


class SqlMetricsReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _sprint_ref(
        self, *, workspace_id: uuid.UUID, sprint_id: uuid.UUID
    ) -> SprintRef | None:
        row = (
            await self._session.execute(
                sa.select(
                    work_orm.SprintRow,
                    work_orm.BoardRow.project_id,
                    work_orm.ProjectRow.mode,
                    WorkspaceRow.timezone,
                    WorkspaceRow.working_days,
                )
                .join(work_orm.BoardRow, work_orm.BoardRow.id == work_orm.SprintRow.board_id)
                .join(work_orm.ProjectRow, work_orm.ProjectRow.id == work_orm.BoardRow.project_id)
                .join(WorkspaceRow, WorkspaceRow.id == work_orm.ProjectRow.workspace_id)
                .where(
                    work_orm.SprintRow.id == sprint_id,
                    work_orm.ProjectRow.workspace_id == workspace_id,
                )
            )
        ).first()
        if row is None:
            return None
        sprint_row, project_id, mode, timezone, working_days = row
        return SprintRef(
            id=sprint_row.id,
            project_id=project_id,
            board_id=sprint_row.board_id,
            name=sprint_row.name,
            start_date=sprint_row.start_date,
            end_date=sprint_row.end_date,
            timezone=timezone,
            working_days=tuple(int(day) for day in working_days.split(",") if day != ""),
            mode=ProjectMode(mode),
        )

    async def _items_for_sprint(self, sprint_id: uuid.UUID) -> list[ItemFlow]:
        assigned_ids = (
            (
                await self._session.execute(
                    sa.select(work_orm.SprintAssignmentRow.work_item_id).where(
                        work_orm.SprintAssignmentRow.sprint_id == sprint_id
                    )
                )
            )
            .scalars()
            .all()
        )
        current_ids = (
            (
                await self._session.execute(
                    sa.select(work_orm.WorkItemRow.id).where(
                        work_orm.WorkItemRow.sprint_id == sprint_id
                    )
                )
            )
            .scalars()
            .all()
        )
        item_ids = {*assigned_ids, *current_ids}
        if not item_ids:
            return []
        rows = (
            (
                await self._session.execute(
                    sa.select(work_orm.WorkItemRow).where(work_orm.WorkItemRow.id.in_(item_ids))
                )
            )
            .scalars()
            .all()
        )
        events = (
            (
                await self._session.execute(
                    sa.select(DomainEventRow)
                    .where(
                        DomainEventRow.aggregate_id.in_(item_ids),
                        DomainEventRow.type.in_(_CATEGORY_EVENT_TYPES),
                    )
                    .order_by(DomainEventRow.occurred_at)
                )
            )
            .scalars()
            .all()
        )
        windows = (
            (
                await self._session.execute(
                    sa.select(work_orm.SprintAssignmentRow).where(
                        work_orm.SprintAssignmentRow.sprint_id == sprint_id,
                        work_orm.SprintAssignmentRow.work_item_id.in_(item_ids),
                    )
                )
            )
            .scalars()
            .all()
        )

        events_by_item: dict[uuid.UUID, list[ItemFlowEvent]] = defaultdict(list)
        for event in events:
            category_value = event.payload.get("to_category") or event.payload.get(
                "status_category"
            )
            if not category_value:
                continue
            events_by_item[event.aggregate_id].append(
                ItemFlowEvent(
                    occurred_at=ensure_utc(event.occurred_at) or event.occurred_at,
                    category=StatusCategory(str(category_value)),
                )
            )
        windows_by_item: dict[uuid.UUID, list[AssignmentWindow]] = defaultdict(list)
        for window in windows:
            windows_by_item[window.work_item_id].append(
                AssignmentWindow(
                    added_at=ensure_utc(window.added_at) or window.added_at,
                    removed_at=ensure_utc(window.removed_at),
                )
            )

        flows: list[ItemFlow] = []
        for row in rows:
            item_windows = sorted(
                windows_by_item.get(row.id, []), key=lambda window: window.added_at
            )
            if not item_windows and row.sprint_id == sprint_id:
                item_windows = [
                    AssignmentWindow(
                        added_at=ensure_utc(row.created_at) or row.created_at, removed_at=None
                    )
                ]
            flows.append(
                ItemFlow(
                    id=row.id,
                    key=row.key,
                    story_points=row.story_points,
                    is_subtask=row.type == WorkItemType.SUBTASK.value,
                    created_at=ensure_utc(row.created_at) or row.created_at,
                    windows=tuple(item_windows),
                    category_events=tuple(events_by_item.get(row.id, [])),
                )
            )
        return flows

    async def sprint_data(
        self, *, workspace_id: uuid.UUID, sprint_id: uuid.UUID
    ) -> SprintMetricsData | None:
        sprint = await self._sprint_ref(workspace_id=workspace_id, sprint_id=sprint_id)
        if sprint is None:
            return None
        return SprintMetricsData(sprint=sprint, items=await self._items_for_sprint(sprint_id))

    async def project_sprints_data(
        self, *, workspace_id: uuid.UUID, project_id: uuid.UUID, last: int | None = None
    ) -> list[SprintMetricsData] | None:
        project_exists = (
            await self._session.execute(
                sa.select(sa.func.count())
                .select_from(work_orm.ProjectRow)
                .where(
                    work_orm.ProjectRow.id == project_id,
                    work_orm.ProjectRow.workspace_id == workspace_id,
                    work_orm.ProjectRow.archived_at.is_(None),
                )
            )
        ).scalar_one()
        if not project_exists:
            return None
        sprint_ids = (
            (
                await self._session.execute(
                    sa.select(work_orm.SprintRow.id)
                    .join(work_orm.BoardRow, work_orm.BoardRow.id == work_orm.SprintRow.board_id)
                    .where(work_orm.BoardRow.project_id == project_id)
                    .order_by(work_orm.SprintRow.start_date)
                )
            )
            .scalars()
            .all()
        )
        if last is not None:
            sprint_ids = sprint_ids[-last:]
        result: list[SprintMetricsData] = []
        for sprint_id in sprint_ids:
            data = await self.sprint_data(workspace_id=workspace_id, sprint_id=sprint_id)
            if data is not None:
                result.append(data)
        return result

    async def flow_items(
        self,
        *,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        since: datetime,
        until: datetime,
    ) -> list[FlowSnapshot] | None:
        project_exists = (
            await self._session.execute(
                sa.select(sa.func.count())
                .select_from(work_orm.ProjectRow)
                .where(
                    work_orm.ProjectRow.id == project_id,
                    work_orm.ProjectRow.workspace_id == workspace_id,
                )
            )
        ).scalar_one()
        if not project_exists:
            return None
        rows = (
            (
                await self._session.execute(
                    sa.select(work_orm.WorkItemRow)
                    .where(
                        work_orm.WorkItemRow.project_id == project_id,
                        work_orm.WorkItemRow.done_at.is_not(None),
                        work_orm.WorkItemRow.done_at >= since,
                        work_orm.WorkItemRow.done_at <= until,
                        work_orm.WorkItemRow.type != WorkItemType.SUBTASK.value,
                    )
                    .order_by(work_orm.WorkItemRow.done_at)
                )
            )
            .scalars()
            .all()
        )
        return [
            FlowSnapshot(
                key=row.key,
                created_at=ensure_utc(row.created_at) or row.created_at,
                first_in_progress_at=ensure_utc(row.first_in_progress_at),
                done_at=ensure_utc(row.done_at) or row.done_at,
            )
            for row in rows
            if row.done_at is not None
        ]
