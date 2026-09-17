"""Rotas HTTP de métricas."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query

from cadencia.identity.interface.deps import SessionDep, WorkspaceAccessDep
from cadencia.metrics.application.queries import (
    ProjectFlowTimesQuery,
    ProjectVelocityQuery,
    SprintBurndownQuery,
    SprintCfdQuery,
)
from cadencia.metrics.infrastructure.reader import SqlMetricsReader
from cadencia.metrics.interface import schemas

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}", tags=["metrics"])


@router.get("/sprints/{sprint_id}/burndown")
async def sprint_burndown(
    sprint_id: uuid.UUID, access: WorkspaceAccessDep, session: SessionDep
) -> schemas.BurndownOut:
    series = await SprintBurndownQuery(SqlMetricsReader(session)).execute(
        workspace_id=access.workspace.id, sprint_id=sprint_id
    )
    return schemas.BurndownOut.model_validate(series)


@router.get("/sprints/{sprint_id}/cfd")
async def sprint_cfd(
    sprint_id: uuid.UUID, access: WorkspaceAccessDep, session: SessionDep
) -> schemas.CfdOut:
    series = await SprintCfdQuery(SqlMetricsReader(session)).execute(
        workspace_id=access.workspace.id, sprint_id=sprint_id
    )
    return schemas.CfdOut.model_validate(series)


@router.get("/projects/{project_id}/velocity")
async def project_velocity(
    project_id: uuid.UUID,
    access: WorkspaceAccessDep,
    session: SessionDep,
    last: int = Query(default=3, ge=1, le=12),
) -> schemas.VelocityOut:
    report = await ProjectVelocityQuery(SqlMetricsReader(session)).execute(
        workspace_id=access.workspace.id, project_id=project_id, last=last
    )
    return schemas.VelocityOut.model_validate(report)


@router.get("/projects/{project_id}/flow-times")
async def project_flow_times(
    project_id: uuid.UUID,
    access: WorkspaceAccessDep,
    session: SessionDep,
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
) -> schemas.FlowTimesOut:
    report = await ProjectFlowTimesQuery(SqlMetricsReader(session)).execute(
        workspace_id=access.workspace.id, project_id=project_id, since=since, until=until
    )
    return schemas.FlowTimesOut.model_validate(report)
