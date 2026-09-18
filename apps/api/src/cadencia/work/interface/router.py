"""Rotas HTTP do contexto work (workspace-scoped — RN-02)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import APIRouter, status
from sqlalchemy.ext.asyncio import AsyncSession

from cadencia.identity.interface.deps import (
    AdminAccessDep,
    SessionDep,
    WorkspaceAccessDep,
    get_clock,
)
from cadencia.shared.clock import Clock
from cadencia.work.application import use_cases
from cadencia.work.infrastructure.repositories import (
    SqlAssignmentRepository,
    SqlBoardRepository,
    SqlProjectRepository,
    SqlSprintRepository,
    SqlWorkItemRepository,
)
from cadencia.work.interface import schemas

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}", tags=["work"])


@dataclass(frozen=True)
class WorkRepos:
    projects: SqlProjectRepository
    boards: SqlBoardRepository
    items: SqlWorkItemRepository
    sprints: SqlSprintRepository
    assignments: SqlAssignmentRepository


def _repos(session: AsyncSession) -> WorkRepos:
    return WorkRepos(
        projects=SqlProjectRepository(session),
        boards=SqlBoardRepository(session),
        items=SqlWorkItemRepository(session),
        sprints=SqlSprintRepository(session),
        assignments=SqlAssignmentRepository(session),
    )


def _clock() -> Clock:
    return get_clock()


@router.get("/projects")
async def list_projects(
    access: WorkspaceAccessDep, session: SessionDep
) -> list[schemas.ProjectOut]:
    repos = _repos(session)
    use_case = use_cases.ListProjects(projects=repos.projects)
    views = await use_case.execute(workspace_id=access.workspace.id)
    return [schemas.ProjectOut.model_validate(view) for view in views]


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: schemas.ProjectCreateRequest, access: WorkspaceAccessDep, session: SessionDep
) -> schemas.ProjectOut:
    repos = _repos(session)
    use_case = use_cases.CreateProject(projects=repos.projects, boards=repos.boards, clock=_clock())
    view = await use_case.execute(
        workspace_id=access.workspace.id,
        name=payload.name,
        key=payload.key,
        mode=payload.mode,
        wip_enforcement=payload.wip_enforcement,
    )
    return schemas.ProjectOut.model_validate(view)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def archive_project(
    project_id: uuid.UUID,
    access: AdminAccessDep,
    session: SessionDep,
) -> None:
    repos = _repos(session)
    await use_cases.ArchiveProject(projects=repos.projects, clock=_clock()).execute(
        workspace_id=access.workspace.id, project_id=project_id
    )


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_item(
    item_id: uuid.UUID,
    access: WorkspaceAccessDep,
    session: SessionDep,
) -> None:
    repos = _repos(session)
    await use_cases.ArchiveWorkItem(
        projects=repos.projects, boards=repos.boards, items=repos.items, clock=_clock()
    ).execute(workspace_id=access.workspace.id, item_id=item_id)


@router.get("/projects/{project_id}/board")
async def get_board(
    project_id: uuid.UUID, access: WorkspaceAccessDep, session: SessionDep
) -> schemas.BoardOut:
    repos = _repos(session)
    use_case = use_cases.GetBoard(projects=repos.projects, boards=repos.boards, items=repos.items)
    view = await use_case.execute(workspace_id=access.workspace.id, project_id=project_id)
    return schemas.BoardOut.model_validate(view)


@router.post(
    "/projects/{project_id}/board/columns",
    status_code=status.HTTP_201_CREATED,
)
async def create_column(
    project_id: uuid.UUID,
    payload: schemas.ColumnCreateRequest,
    access: WorkspaceAccessDep,
    session: SessionDep,
) -> schemas.BoardOut:
    repos = _repos(session)
    use_case = use_cases.CreateBoardColumn(
        projects=repos.projects, boards=repos.boards, items=repos.items
    )
    view = await use_case.execute(
        workspace_id=access.workspace.id,
        project_id=project_id,
        name=payload.name,
        category=payload.category,
        wip_limit=payload.wip_limit,
    )
    return schemas.BoardOut.model_validate(view)


@router.patch("/projects/{project_id}/board/columns/{column_id}")
async def update_column(
    project_id: uuid.UUID,
    column_id: uuid.UUID,
    payload: schemas.ColumnUpdateRequest,
    access: WorkspaceAccessDep,
    session: SessionDep,
) -> schemas.BoardOut:
    repos = _repos(session)
    use_case = use_cases.UpdateBoardColumn(
        projects=repos.projects, boards=repos.boards, items=repos.items
    )
    view = await use_case.execute(
        workspace_id=access.workspace.id,
        project_id=project_id,
        column_id=column_id,
        name=payload.name,
        wip_limit=payload.wip_limit,
        clear_wip=payload.clear_wip,
    )
    return schemas.BoardOut.model_validate(view)


@router.delete("/projects/{project_id}/board/columns/{column_id}")
async def delete_column(
    project_id: uuid.UUID,
    column_id: uuid.UUID,
    access: WorkspaceAccessDep,
    session: SessionDep,
) -> schemas.BoardOut:
    repos = _repos(session)
    use_case = use_cases.DeleteBoardColumn(
        projects=repos.projects, boards=repos.boards, items=repos.items
    )
    view = await use_case.execute(
        workspace_id=access.workspace.id, project_id=project_id, column_id=column_id
    )
    return schemas.BoardOut.model_validate(view)


@router.put("/projects/{project_id}/board/columns/order")
async def reorder_columns(
    project_id: uuid.UUID,
    payload: schemas.ColumnOrderRequest,
    access: WorkspaceAccessDep,
    session: SessionDep,
) -> schemas.BoardOut:
    repos = _repos(session)
    use_case = use_cases.ReorderBoardColumns(
        projects=repos.projects, boards=repos.boards, items=repos.items
    )
    view = await use_case.execute(
        workspace_id=access.workspace.id,
        project_id=project_id,
        column_ids=payload.column_ids,
    )
    return schemas.BoardOut.model_validate(view)


@router.get("/projects/{project_id}/items")
async def list_items(
    project_id: uuid.UUID, access: WorkspaceAccessDep, session: SessionDep
) -> list[schemas.WorkItemOut]:
    repos = _repos(session)
    use_case = use_cases.ListItems(projects=repos.projects, boards=repos.boards, items=repos.items)
    views = await use_case.execute(workspace_id=access.workspace.id, project_id=project_id)
    return [schemas.WorkItemOut.model_validate(view) for view in views]


@router.post(
    "/projects/{project_id}/items",
    status_code=status.HTTP_201_CREATED,
)
async def create_item(
    project_id: uuid.UUID,
    payload: schemas.WorkItemCreateRequest,
    access: WorkspaceAccessDep,
    session: SessionDep,
) -> schemas.WorkItemOut:
    repos = _repos(session)
    use_case = use_cases.CreateWorkItem(
        projects=repos.projects, boards=repos.boards, items=repos.items, clock=_clock()
    )
    view = await use_case.execute(
        workspace_id=access.workspace.id,
        project_id=project_id,
        item_type=payload.type,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        story_points=payload.story_points,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
        parent_id=payload.parent_id,
    )
    return schemas.WorkItemOut.model_validate(view)


@router.patch("/items/{item_id}")
async def update_item(
    item_id: uuid.UUID,
    payload: schemas.WorkItemUpdateRequest,
    access: WorkspaceAccessDep,
    session: SessionDep,
) -> schemas.WorkItemOut:
    repos = _repos(session)
    use_case = use_cases.UpdateWorkItem(
        projects=repos.projects, boards=repos.boards, items=repos.items, clock=_clock()
    )
    view = await use_case.execute(
        workspace_id=access.workspace.id,
        item_id=item_id,
        expected_version=payload.expected_version,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        clear_assignee=payload.clear_assignee,
        story_points=payload.story_points,
        clear_points=payload.clear_points,
        due_date=payload.due_date,
        clear_due_date=payload.clear_due_date,
    )
    return schemas.WorkItemOut.model_validate(view)


@router.post("/items/{item_id}/move")
async def move_item(
    item_id: uuid.UUID,
    payload: schemas.WorkItemMoveRequest,
    access: WorkspaceAccessDep,
    session: SessionDep,
) -> schemas.WorkItemMoveResponse:
    repos = _repos(session)
    use_case = use_cases.MoveWorkItem(
        projects=repos.projects, boards=repos.boards, items=repos.items, clock=_clock()
    )
    result = await use_case.execute(
        workspace_id=access.workspace.id,
        item_id=item_id,
        target_column_id=payload.column_id,
        target_index=payload.index,
        expected_version=payload.expected_version,
    )
    return schemas.WorkItemMoveResponse(
        item=schemas.WorkItemOut.model_validate(result.item),
        wip_warning=result.wip_warning,
    )


@router.put("/items/{item_id}/sprint")
async def assign_item_sprint(
    item_id: uuid.UUID,
    payload: schemas.AssignSprintRequest,
    access: WorkspaceAccessDep,
    session: SessionDep,
) -> schemas.WorkItemOut:
    repos = _repos(session)
    use_case = use_cases.AssignWorkItemToSprint(
        projects=repos.projects,
        boards=repos.boards,
        items=repos.items,
        sprints=repos.sprints,
        assignments=repos.assignments,
        clock=_clock(),
    )
    view = await use_case.execute(
        workspace_id=access.workspace.id, item_id=item_id, sprint_id=payload.sprint_id
    )
    return schemas.WorkItemOut.model_validate(view)


@router.get("/projects/{project_id}/sprints")
async def list_sprints(
    project_id: uuid.UUID, access: WorkspaceAccessDep, session: SessionDep
) -> list[schemas.SprintOut]:
    repos = _repos(session)
    use_case = use_cases.ListSprints(
        projects=repos.projects, items=repos.items, sprints=repos.sprints
    )
    views = await use_case.execute(workspace_id=access.workspace.id, project_id=project_id)
    return [schemas.SprintOut.model_validate(view) for view in views]


@router.post(
    "/projects/{project_id}/sprints",
    status_code=status.HTTP_201_CREATED,
)
async def create_sprint(
    project_id: uuid.UUID,
    payload: schemas.SprintCreateRequest,
    access: WorkspaceAccessDep,
    session: SessionDep,
) -> schemas.SprintOut:
    repos = _repos(session)
    use_case = use_cases.CreateSprint(
        projects=repos.projects, boards=repos.boards, sprints=repos.sprints, clock=_clock()
    )
    view = await use_case.execute(
        workspace_id=access.workspace.id,
        project_id=project_id,
        name=payload.name,
        goal=payload.goal,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    return schemas.SprintOut.model_validate(view)


@router.get("/sprints/{sprint_id}")
async def get_sprint(
    sprint_id: uuid.UUID, access: WorkspaceAccessDep, session: SessionDep
) -> schemas.SprintOut:
    repos = _repos(session)
    use_case = use_cases.GetSprint(
        projects=repos.projects, boards=repos.boards, items=repos.items, sprints=repos.sprints
    )
    view = await use_case.execute(workspace_id=access.workspace.id, sprint_id=sprint_id)
    return schemas.SprintOut.model_validate(view)


@router.post("/sprints/{sprint_id}/start")
async def start_sprint(
    sprint_id: uuid.UUID, access: WorkspaceAccessDep, session: SessionDep
) -> schemas.SprintOut:
    repos = _repos(session)
    use_case = use_cases.StartSprint(
        projects=repos.projects,
        boards=repos.boards,
        items=repos.items,
        sprints=repos.sprints,
        clock=_clock(),
    )
    view = await use_case.execute(workspace_id=access.workspace.id, sprint_id=sprint_id)
    return schemas.SprintOut.model_validate(view)


@router.post("/sprints/{sprint_id}/complete")
async def complete_sprint(
    sprint_id: uuid.UUID,
    payload: schemas.CompleteSprintRequest,
    access: WorkspaceAccessDep,
    session: SessionDep,
) -> schemas.SprintOut:
    repos = _repos(session)
    use_case = use_cases.CompleteSprint(
        projects=repos.projects,
        boards=repos.boards,
        items=repos.items,
        sprints=repos.sprints,
        assignments=repos.assignments,
        clock=_clock(),
    )
    view = await use_case.execute(
        workspace_id=access.workspace.id,
        sprint_id=sprint_id,
        target_sprint_id=payload.target_sprint_id,
    )
    return schemas.SprintOut.model_validate(view)
