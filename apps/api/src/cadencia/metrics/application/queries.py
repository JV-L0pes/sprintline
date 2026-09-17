"""Consultas de métricas — orquestram leitura + calculadoras puras."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from cadencia.metrics.application.ports import MetricsReader
from cadencia.metrics.domain.calculators import (
    build_burndown,
    build_cfd,
    build_flow_times,
    build_velocity,
)
from cadencia.metrics.domain.models import BurndownSeries, CfdSeries, FlowTimes, VelocityReport
from cadencia.shared.errors import NotFoundError


class SprintBurndownQuery:
    def __init__(self, reader: MetricsReader) -> None:
        self._reader = reader

    async def execute(self, *, workspace_id: uuid.UUID, sprint_id: uuid.UUID) -> BurndownSeries:
        data = await self._reader.sprint_data(workspace_id=workspace_id, sprint_id=sprint_id)
        if data is None:
            raise NotFoundError("Sprint não encontrada", code="SPRINT_NOT_FOUND")
        return build_burndown(data)


class SprintCfdQuery:
    def __init__(self, reader: MetricsReader) -> None:
        self._reader = reader

    async def execute(self, *, workspace_id: uuid.UUID, sprint_id: uuid.UUID) -> CfdSeries:
        data = await self._reader.sprint_data(workspace_id=workspace_id, sprint_id=sprint_id)
        if data is None:
            raise NotFoundError("Sprint não encontrada", code="SPRINT_NOT_FOUND")
        sprint = data.sprint
        return build_cfd(
            sprint_id=sprint.id,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            working_days=sprint.working_days,
            timezone=sprint.timezone,
            items=data.items,
        )


class ProjectVelocityQuery:
    def __init__(self, reader: MetricsReader) -> None:
        self._reader = reader

    async def execute(
        self, *, workspace_id: uuid.UUID, project_id: uuid.UUID, last: int = 3
    ) -> VelocityReport:
        data = await self._reader.project_sprints_data(
            workspace_id=workspace_id, project_id=project_id, last=max(1, min(last, 12))
        )
        if data is None:
            raise NotFoundError("Projeto não encontrado", code="PROJECT_NOT_FOUND")
        series = [build_burndown(sprint_data) for sprint_data in data]
        return build_velocity(series, average_window=last)


class ProjectFlowTimesQuery:
    def __init__(self, reader: MetricsReader) -> None:
        self._reader = reader

    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> FlowTimes:
        end = until or datetime.now(UTC)
        start = since or (end - timedelta(weeks=12))
        items = await self._reader.flow_items(
            workspace_id=workspace_id, project_id=project_id, since=start, until=end
        )
        if items is None:
            raise NotFoundError("Projeto não encontrado", code="PROJECT_NOT_FOUND")
        return build_flow_times(items)
