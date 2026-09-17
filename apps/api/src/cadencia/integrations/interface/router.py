"""Rotas HTTP de integracao com o Jira."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from cadencia.identity.domain.value_objects import Role
from cadencia.identity.interface.deps import (
    CurrentUser,
    SessionDep,
    WorkspaceAccessDep,
    get_clock,
    require_role,
)
from cadencia.integrations.application.trello import (
    ConnectTrello,
    HandleTrelloWebhook,
    ListTrelloBoards,
    RunTrelloImportChunk,
    StartTrelloAuthorize,
    StartTrelloImport,
)
from cadencia.integrations.application.use_cases import (
    CompleteJiraOAuth,
    DisconnectIntegration,
    DiscoverJiraFields,
    HandleJiraWebhook,
    JiraConnectionService,
    ListIntegrations,
    RunJiraImportChunk,
    StartJiraImport,
    StartJiraOAuth,
    job_view,
)
from cadencia.integrations.infrastructure.jira_client import HttpxJiraGateway
from cadencia.integrations.infrastructure.repositories import (
    SqlExternalMappingRepository,
    SqlIntegrationRepository,
    SqlSyncJobRepository,
    SqlTokenStore,
    SqlWebhookEventRepository,
)
from cadencia.integrations.infrastructure.trello_client import HttpxTrelloGateway
from cadencia.integrations.infrastructure.vault import TokenVault
from cadencia.integrations.interface import schemas
from cadencia.platform.security import webhook_token
from cadencia.shared.errors import NotFoundError
from cadencia.work.application.use_cases import CreateWorkItem, MoveWorkItem
from cadencia.work.infrastructure.repositories import (
    SqlBoardRepository,
    SqlProjectRepository,
    SqlWorkItemRepository,
)

router = APIRouter(tags=["integrations"])


def _gateway(request: Request) -> HttpxJiraGateway:
    """Permite injetar um gateway fake (testes/dev) via `app.state.jira_gateway`."""
    injected = getattr(request.app.state, "jira_gateway", None)
    if injected is not None:
        return injected
    return HttpxJiraGateway(request.app.state.settings)


def _trello_gateway(request: Request) -> HttpxTrelloGateway:
    """Permite injetar um gateway fake (testes/dev) via `app.state.trello_gateway`."""
    injected = getattr(request.app.state, "trello_gateway", None)
    if injected is not None:
        return injected
    return HttpxTrelloGateway(request.app.state.settings)


def _vault(request: Request) -> TokenVault:
    return TokenVault(request.app.state.settings.fernet_key)


def _service(request: Request, session: AsyncSession) -> JiraConnectionService:
    return JiraConnectionService(
        SqlIntegrationRepository(session),
        SqlTokenStore(session, _vault(request)),
        _gateway(request),
        get_clock(),
    )


def _work_use_cases(session: AsyncSession) -> tuple[CreateWorkItem, MoveWorkItem]:
    projects = SqlProjectRepository(session)
    boards = SqlBoardRepository(session)
    items = SqlWorkItemRepository(session)
    clock = get_clock()
    return (
        CreateWorkItem(projects, boards, items, clock),
        MoveWorkItem(projects, boards, items, clock),
    )


@router.get("/api/v1/workspaces/{workspace_id}/integrations")
async def list_integrations(
    access: WorkspaceAccessDep, session: SessionDep
) -> list[schemas.IntegrationOut]:
    views = await ListIntegrations(SqlIntegrationRepository(session)).execute(
        workspace_id=access.workspace.id
    )
    return [schemas.IntegrationOut.model_validate(view) for view in views]


@router.post(
    "/api/v1/workspaces/{workspace_id}/integrations/jira/authorize",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def jira_authorize(
    request: Request,
    user: CurrentUser,
    workspace_id: uuid.UUID,
) -> schemas.AuthorizeOut:
    authorize_url = await StartJiraOAuth(
        _gateway(request), request.app.state.settings, get_clock()
    ).execute(workspace_id=workspace_id, user_id=user.id)
    return schemas.AuthorizeOut(authorize_url=authorize_url)


@router.get("/api/v1/integrations/jira/callback")
async def jira_callback(
    request: Request,
    session: SessionDep,
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    settings = request.app.state.settings
    try:
        view = await CompleteJiraOAuth(
            _gateway(request),
            SqlIntegrationRepository(session),
            SqlTokenStore(session, _vault(request)),
            settings,
            get_clock(),
        ).execute(code=code, state=state)
    except Exception:
        return RedirectResponse(
            f"{settings.web_base_url}/integrations/callback?status=error",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    return RedirectResponse(
        f"{settings.web_base_url}/integrations/callback?status=connected&workspace_id={view.id}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


@router.post(
    "/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/fields",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def discover_fields(
    request: Request,
    workspace_id: uuid.UUID,
    connection_id: uuid.UUID,
    session: SessionDep,
) -> schemas.FieldDiscoveryOut:
    view = await DiscoverJiraFields(
        _service(request, session), SqlIntegrationRepository(session), _gateway(request)
    ).execute(workspace_id=workspace_id, connection_id=connection_id)
    return schemas.FieldDiscoveryOut(
        story_points_field=view.story_points_field,
        fields=[
            schemas.JiraFieldOut(
                field_id=field.field_id, name=field.name, schema_type=field.schema_type
            )
            for field in view.fields
        ],
    )


@router.post(
    "/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/import",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def start_import(
    workspace_id: uuid.UUID,
    connection_id: uuid.UUID,
    payload: schemas.ImportStartRequest,
    session: SessionDep,
) -> schemas.JobOut:
    view = await StartJiraImport(
        SqlIntegrationRepository(session), SqlSyncJobRepository(session), get_clock()
    ).execute(
        workspace_id=workspace_id, connection_id=connection_id, project_key=payload.project_key
    )
    return schemas.JobOut.model_validate(view)


@router.get("/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/jobs")
async def list_jobs(
    access: WorkspaceAccessDep, session: SessionDep, connection_id: uuid.UUID
) -> list[schemas.JobOut]:
    integration = await SqlIntegrationRepository(session).get(connection_id, access.workspace.id)
    if integration is None:
        raise NotFoundError("Integracao nao encontrada", code="INTEGRATION_NOT_FOUND")
    jobs = await SqlSyncJobRepository(session).list_for_connection(integration.id)
    return [schemas.JobOut.model_validate(job_view(job)) for job in jobs]


@router.post(
    "/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/jobs/{job_id}/run",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def run_import_chunk(
    request: Request,
    workspace_id: uuid.UUID,
    connection_id: uuid.UUID,
    job_id: uuid.UUID,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=100),
) -> schemas.JobOut:
    integration = await SqlIntegrationRepository(session).get(connection_id, workspace_id)
    if integration is None:
        raise NotFoundError("Integracao nao encontrada", code="INTEGRATION_NOT_FOUND")
    create_item, move_item = _work_use_cases(session)
    if integration.provider == "TRELLO":
        view = await RunTrelloImportChunk(
            SqlIntegrationRepository(session),
            SqlSyncJobRepository(session),
            SqlExternalMappingRepository(session),
            SqlTokenStore(session, _vault(request)),
            _trello_gateway(request),
            SqlProjectRepository(session),
            SqlBoardRepository(session),
            create_item,
            move_item,
            request.app.state.settings,
            get_clock(),
        ).execute(
            workspace_id=workspace_id,
            connection_id=connection_id,
            job_id=job_id,
            limit=limit,
        )
        return schemas.JobOut.model_validate(view)
    view = await RunJiraImportChunk(
        SqlIntegrationRepository(session),
        SqlSyncJobRepository(session),
        SqlExternalMappingRepository(session),
        _service(request, session),
        _gateway(request),
        SqlProjectRepository(session),
        SqlBoardRepository(session),
        SqlWorkItemRepository(session),
        create_item,
        move_item,
        get_clock(),
    ).execute(
        workspace_id=workspace_id,
        connection_id=connection_id,
        job_id=job_id,
        limit=limit,
    )
    return schemas.JobOut.model_validate(view)


@router.post(
    "/api/v1/workspaces/{workspace_id}/integrations/trello/authorize",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def trello_authorize(request: Request) -> schemas.AuthorizeOut:
    authorize_url = await StartTrelloAuthorize(
        _trello_gateway(request), request.app.state.settings
    ).execute()
    return schemas.AuthorizeOut(authorize_url=authorize_url)


@router.post(
    "/api/v1/workspaces/{workspace_id}/integrations/trello/connect",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def trello_connect(
    request: Request,
    workspace_id: uuid.UUID,
    payload: schemas.TrelloConnectRequest,
    session: SessionDep,
) -> schemas.IntegrationOut:
    view = await ConnectTrello(
        _trello_gateway(request),
        SqlIntegrationRepository(session),
        SqlTokenStore(session, _vault(request)),
        get_clock(),
    ).execute(workspace_id=workspace_id, token=payload.token)
    return schemas.IntegrationOut.model_validate(view)


@router.get("/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/trello/boards")
async def trello_boards(
    request: Request,
    access: WorkspaceAccessDep,
    session: SessionDep,
    connection_id: uuid.UUID,
) -> list[schemas.TrelloBoardOut]:
    views = await ListTrelloBoards(
        _trello_gateway(request),
        SqlIntegrationRepository(session),
        SqlTokenStore(session, _vault(request)),
    ).execute(workspace_id=access.workspace.id, connection_id=connection_id)
    return [schemas.TrelloBoardOut.model_validate(view) for view in views]


@router.post(
    "/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/trello/import",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def trello_import(
    workspace_id: uuid.UUID,
    connection_id: uuid.UUID,
    payload: schemas.TrelloImportRequest,
    session: SessionDep,
) -> schemas.JobOut:
    view = await StartTrelloImport(
        SqlIntegrationRepository(session), SqlSyncJobRepository(session), get_clock()
    ).execute(workspace_id=workspace_id, connection_id=connection_id, board_id=payload.board_id)
    return schemas.JobOut.model_validate(view)


@router.post("/api/v1/integrations/trello/webhook/{connection_id}")
async def trello_webhook(
    request: Request,
    connection_id: uuid.UUID,
    session: SessionDep,
    token: str = Query(...),
) -> dict[str, Any]:
    settings = request.app.state.settings
    if token != webhook_token(str(connection_id), settings):
        raise NotFoundError("Webhook nao encontrado", code="WEBHOOK_NOT_FOUND")
    payload = await request.json()
    _, move_item = _work_use_cases(session)
    accepted = await HandleTrelloWebhook(
        SqlIntegrationRepository(session),
        SqlWebhookEventRepository(session),
        SqlExternalMappingRepository(session),
        SqlTokenStore(session, _vault(request)),
        _trello_gateway(request),
        move_item,
        get_clock(),
    ).execute(connection_id=connection_id, payload=payload)
    return {"status": "accepted" if accepted else "duplicate"}


@router.delete(
    "/api/v1/workspaces/{workspace_id}/integrations/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def disconnect(
    request: Request,
    workspace_id: uuid.UUID,
    connection_id: uuid.UUID,
    session: SessionDep,
) -> None:
    await DisconnectIntegration(
        SqlIntegrationRepository(session),
        SqlTokenStore(session, _vault(request)),
        SqlExternalMappingRepository(session),
    ).execute(workspace_id=workspace_id, connection_id=connection_id)


@router.post("/api/v1/integrations/jira/webhook/{connection_id}")
async def jira_webhook(
    request: Request,
    connection_id: uuid.UUID,
    session: SessionDep,
    token: str = Query(...),
) -> dict[str, Any]:
    settings = request.app.state.settings
    if token != webhook_token(str(connection_id), settings):
        raise NotFoundError("Webhook nao encontrado", code="WEBHOOK_NOT_FOUND")
    payload = await request.json()
    _, move_item = _work_use_cases(session)
    accepted = await HandleJiraWebhook(
        SqlIntegrationRepository(session),
        SqlWebhookEventRepository(session),
        SqlExternalMappingRepository(session),
        SqlBoardRepository(session),
        SqlWorkItemRepository(session),
        move_item,
        get_clock(),
    ).execute(connection_id=connection_id, payload=payload)
    return {"status": "accepted" if accepted else "duplicate"}
