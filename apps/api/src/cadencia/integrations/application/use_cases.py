"""Casos de uso do contexto integrations (Jira Cloud)."""

from __future__ import annotations

import re
import uuid
from datetime import timedelta
from typing import Any

from cadencia.integrations.application.dto import (
    FieldDiscoveryView,
    IntegrationView,
    JiraFieldView,
    SyncJobView,
)
from cadencia.integrations.application.project_import import ensure_import_project
from cadencia.integrations.domain.entities import Integration, SyncJob
from cadencia.integrations.domain.ports import JiraGateway
from cadencia.integrations.domain.repositories import (
    ExternalMappingRepository,
    IntegrationRepository,
    SyncJobRepository,
    TokenStore,
    WebhookEventRepository,
)
from cadencia.platform.config import Settings
from cadencia.platform.security import decode_state_token, encode_state_token
from cadencia.shared.clock import Clock
from cadencia.shared.errors import NotFoundError, UnauthorizedError, ValidationError
from cadencia.work.application.use_cases import CreateProject, CreateWorkItem, MoveWorkItem
from cadencia.work.domain.repositories import BoardRepository, ProjectRepository, WorkItemRepository
from cadencia.work.domain.value_objects import (
    FIBONACCI_POINTS,
    Priority,
    StatusCategory,
    WorkItemType,
)

_JIRA_TYPE_MAP: dict[str, WorkItemType] = {
    "epic": WorkItemType.EPIC,
    "story": WorkItemType.STORY,
    "task": WorkItemType.TASK,
    "bug": WorkItemType.BUG,
    "sub-task": WorkItemType.SUBTASK,
    "subtask": WorkItemType.SUBTASK,
}

_JIRA_CATEGORY_MAP: dict[str, StatusCategory] = {
    "todo": StatusCategory.TODO,
    "in progress": StatusCategory.IN_PROGRESS,
    "done": StatusCategory.DONE,
}

_STORY_POINTS_HINT = re.compile(r"story\s*points?|pontos?", re.IGNORECASE)


def integration_view(integration: Integration) -> IntegrationView:
    return IntegrationView(
        id=integration.id,
        provider=integration.provider,
        site_url=integration.site_url,
        status=integration.status,
        story_points_field=integration.field_map.get("story_points_field"),
        created_at=integration.created_at,
    )


def job_view(job: SyncJob) -> SyncJobView:
    return SyncJobView(
        id=job.id,
        job_type=job.job_type,
        state=job.state,
        project_key=job.cursor.project_key,
        start_at=job.cursor.start_at,
        imported_count=job.imported_count,
        last_error=job.last_error,
        created_at=job.created_at,
    )


def snap_story_points(value: float | None) -> int | None:
    """Arredonda um valor do Jira para o Fibonacci mais próximo (RN-10)."""
    if value is None or value <= 0:
        return None
    candidates = sorted(FIBONACCI_POINTS)
    return min(candidates, key=lambda candidate: abs(candidate - value))


class JiraConnectionService:
    """Obtem access token válido, renovando via refresh quando necessario."""

    def __init__(
        self,
        connections: IntegrationRepository,
        tokens: TokenStore,
        gateway: JiraGateway,
        clock: Clock,
    ) -> None:
        self._connections = connections
        self._tokens = tokens
        self._gateway = gateway
        self._clock = clock

    async def access_token(self, integration: Integration) -> str:
        stored = await self._tokens.load(integration.id)
        if stored is None or not stored.refresh_token:
            raise NotFoundError(
                "Tokens da integração não encontrados; reconecte o Jira",
                code="TOKENS_MISSING",
            )
        now = self._clock.now()
        if (
            stored.access_token
            and stored.access_expires_at is not None
            and stored.access_expires_at - now > timedelta(seconds=60)
        ):
            return stored.access_token
        refreshed = await self._gateway.refresh_access_token(stored.refresh_token)
        expires_at = now + timedelta(seconds=refreshed.expires_in)
        await self._tokens.save(
            integration.id,
            access_token=refreshed.access_token,
            refresh_token=refreshed.refresh_token or stored.refresh_token,
            access_expires_at=expires_at,
        )
        return refreshed.access_token


class StartJiraOAuth:
    def __init__(self, gateway: JiraGateway, settings: Settings, clock: Clock) -> None:
        self._gateway = gateway
        self._settings = settings
        self._clock = clock

    async def execute(self, *, workspace_id: uuid.UUID, user_id: uuid.UUID) -> str:
        if not self._settings.jira_client_id:
            raise ValidationError(
                "JIRA_CLIENT_ID não configurado no servidor", code="JIRA_NOT_CONFIGURED"
            )
        state = encode_state_token(
            {
                "typ": "jira_oauth",
                "wid": str(workspace_id),
                "uid": str(user_id),
                "nonce": uuid.uuid4().hex,
            },
            settings=self._settings,
            now=self._clock.now(),
        )
        return self._gateway.build_authorize_url(state)


class CompleteJiraOAuth:
    def __init__(
        self,
        gateway: JiraGateway,
        connections: IntegrationRepository,
        tokens: TokenStore,
        settings: Settings,
        clock: Clock,
    ) -> None:
        self._gateway = gateway
        self._connections = connections
        self._tokens = tokens
        self._settings = settings
        self._clock = clock

    async def execute(self, *, code: str, state: str) -> IntegrationView:
        claims = decode_state_token(state, settings=self._settings)
        if claims.get("typ") != "jira_oauth":
            raise UnauthorizedError("State OAuth inválido", code="INVALID_OAUTH_STATE")
        workspace_id = uuid.UUID(claims["wid"])
        oauth = await self._gateway.exchange_code(code)
        sites = await self._gateway.accessible_resources(oauth.access_token)
        if not sites:
            raise ValidationError("Nenhum site Jira acessível para esta conta", code="NO_JIRA_SITE")
        site = sites[0]
        now = self._clock.now()
        integration = Integration.connect(
            workspace_id=workspace_id,
            provider="JIRA",
            cloud_id=site.cloud_id,
            site_url=site.url,
            now=now,
        )
        refresh = oauth.refresh_token or ""
        if not refresh:
            raise ValidationError(
                "Jira não retornou refresh_token; inclua offline_access no escopo",
                code="JIRA_MISSING_REFRESH_TOKEN",
            )
        await self._connections.add(integration)
        await self._tokens.save(
            integration.id,
            access_token=oauth.access_token,
            refresh_token=refresh,
            access_expires_at=now + timedelta(seconds=oauth.expires_in),
        )
        return integration_view(integration)


class ListIntegrations:
    def __init__(self, connections: IntegrationRepository) -> None:
        self._connections = connections

    async def execute(self, *, workspace_id: uuid.UUID) -> list[IntegrationView]:
        integrations = await self._connections.list_for_workspace(workspace_id)
        return [integration_view(integration) for integration in integrations]


class DisconnectIntegration:
    def __init__(
        self,
        connections: IntegrationRepository,
        tokens: TokenStore,
        mappings: ExternalMappingRepository,
    ) -> None:
        self._connections = connections
        self._tokens = tokens
        self._mappings = mappings

    async def execute(self, *, workspace_id: uuid.UUID, connection_id: uuid.UUID) -> None:
        integration = await self._connections.get(connection_id, workspace_id)
        if integration is None:
            raise NotFoundError("Integração não encontrada", code="INTEGRATION_NOT_FOUND")
        await self._tokens.clear(integration.id)
        await self._mappings.delete_for_connection(integration.id)
        await self._connections.delete(integration)


class DiscoverJiraFields:
    def __init__(
        self,
        service: JiraConnectionService,
        connections: IntegrationRepository,
        gateway: JiraGateway,
    ) -> None:
        self._service = service
        self._connections = connections
        self._gateway = gateway

    async def execute(
        self, *, workspace_id: uuid.UUID, connection_id: uuid.UUID
    ) -> FieldDiscoveryView:
        integration = await self._connections.get(connection_id, workspace_id)
        if integration is None:
            raise NotFoundError("Integração não encontrada", code="INTEGRATION_NOT_FOUND")
        token = await self._service.access_token(integration)
        fields = await self._gateway.list_fields(token, integration.cloud_id)
        candidates = [
            field
            for field in fields
            if field.schema_type in {"number", "float", "integer"}
            and _STORY_POINTS_HINT.search(field.name)
        ]
        chosen = candidates[0].field_id if candidates else None
        if chosen:
            integration.set_field_map({"story_points_field": chosen})
            await self._connections.save(integration)
        return FieldDiscoveryView(
            story_points_field=chosen,
            fields=[
                JiraFieldView(
                    field_id=field.field_id, name=field.name, schema_type=field.schema_type
                )
                for field in fields
            ],
        )


class StartJiraImport:
    def __init__(
        self,
        connections: IntegrationRepository,
        jobs: SyncJobRepository,
        clock: Clock,
    ) -> None:
        self._connections = connections
        self._jobs = jobs
        self._clock = clock

    async def execute(
        self, *, workspace_id: uuid.UUID, connection_id: uuid.UUID, project_key: str
    ) -> SyncJobView:
        integration = await self._connections.get(connection_id, workspace_id)
        if integration is None:
            raise NotFoundError("Integração não encontrada", code="INTEGRATION_NOT_FOUND")
        job = SyncJob.start_import(
            connection_id=integration.id,
            project_key=project_key.strip().upper(),
            now=self._clock.now(),
        )
        await self._jobs.add(job)
        return job_view(job)


class RunJiraImportChunk:
    """Importa um lote de issues do Jira de forma idempotente e resumivel (RN-20)."""

    def __init__(
        self,
        connections: IntegrationRepository,
        jobs: SyncJobRepository,
        mappings: ExternalMappingRepository,
        service: JiraConnectionService,
        gateway: JiraGateway,
        projects: ProjectRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
        create_item: CreateWorkItem,
        move_item: MoveWorkItem,
        clock: Clock,
    ) -> None:
        self._connections = connections
        self._jobs = jobs
        self._mappings = mappings
        self._service = service
        self._gateway = gateway
        self._projects = projects
        self._boards = boards
        self._items = items
        self._create_item = create_item
        self._move_item = move_item
        self._clock = clock

    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        connection_id: uuid.UUID,
        job_id: uuid.UUID,
        limit: int = 50,
    ) -> SyncJobView:
        integration = await self._connections.get(connection_id, workspace_id)
        if integration is None:
            raise NotFoundError("Integração não encontrada", code="INTEGRATION_NOT_FOUND")
        job = await self._jobs.get(job_id)
        if job is None or job.connection_id != integration.id:
            raise NotFoundError("Job de importação não encontrado", code="JOB_NOT_FOUND")
        now = self._clock.now()
        job.mark_running(now)
        token = await self._service.access_token(integration)
        project, board = await ensure_import_project(
            projects=self._projects,
            boards=self._boards,
            create_project=CreateProject(
                projects=self._projects, boards=self._boards, clock=self._clock
            ),
            mappings=self._mappings,
            connection_id=integration.id,
            workspace_id=workspace_id,
            external_id=job.cursor.project_key,
            name=f"{job.cursor.project_key} (Jira)",
            preferred_key=job.cursor.project_key,
        )
        issues, has_more = await self._gateway.search_issues(
            token,
            integration.cloud_id,
            job.cursor.project_key,
            start_at=job.cursor.start_at,
            max_results=limit,
            story_points_field=integration.field_map.get("story_points_field"),
        )
        imported = 0
        for issue in issues:
            issue_type = _JIRA_TYPE_MAP.get(issue.issue_type.lower())
            if issue_type is None or issue_type is WorkItemType.SUBTASK:
                continue
            if await self._mappings.find(integration.id, "issue", issue.key) is not None:
                continue
            view = await self._create_item.execute(
                workspace_id=workspace_id,
                project_id=project.id,
                item_type=issue_type,
                title=issue.summary or f"{issue.key} (importado do Jira)",
                description=f"Importado do Jira: {issue.key} ({integration.site_url})",
                priority=Priority.MEDIUM,
                story_points=snap_story_points(issue.story_points),
            )
            target_column = _find_column(board, _JIRA_CATEGORY_MAP.get(issue.status_category))
            if target_column is not None and target_column.id != view.status_column_id:
                await self._move_item.execute(
                    workspace_id=workspace_id,
                    item_id=view.id,
                    target_column_id=target_column.id,
                    target_index=10**6,
                )
            await self._mappings.save(integration.id, "issue", issue.key, view.id)
            imported += 1
        job.advance(
            imported=imported,
            next_start_at=job.cursor.start_at + len(issues),
            has_more=has_more,
            now=now,
        )
        await self._jobs.save(job)
        return job_view(job)


class HandleJiraWebhook:
    """Processa webhooks do Jira com deduplicacao por evento (RN-20)."""

    def __init__(
        self,
        connections: IntegrationRepository,
        webhooks: WebhookEventRepository,
        mappings: ExternalMappingRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
        move_item: MoveWorkItem,
        clock: Clock,
    ) -> None:
        self._connections = connections
        self._webhooks = webhooks
        self._mappings = mappings
        self._boards = boards
        self._items = items
        self._move_item = move_item
        self._clock = clock

    async def execute(self, *, connection_id: uuid.UUID, payload: dict[str, Any]) -> bool:
        integration = await self._connections.get_by_id(connection_id)
        if integration is None or integration.status != "CONNECTED":
            raise NotFoundError("Integração não encontrada", code="INTEGRATION_NOT_FOUND")
        event_type = str(payload.get("webhookEvent", ""))
        issue = payload.get("issue") or {}
        issue_key = str(issue.get("key", ""))
        external_id = f"{event_type}:{payload.get('timestamp', '')}:{issue_key}"
        now = self._clock.now()
        if not await self._webhooks.register(integration.id, external_id, now):
            return False
        if event_type not in {"jira:issue_created", "jira:issue_updated"} or not issue_key:
            return True
        internal_id = await self._mappings.find(integration.id, "issue", issue_key)
        if internal_id is None:
            return True
        item = await self._items.get(internal_id)
        if item is None:
            return True
        board = await self._boards.get_by_project(item.project_id)
        if board is None:
            return True
        category_key = (
            ((issue.get("fields") or {}).get("status") or {})
            .get("statusCategory", {})
            .get("key", "new")
        )
        category = {"new": "todo", "indeterminate": "in progress", "done": "done"}.get(
            str(category_key).lower(), "todo"
        )
        column = _find_column(board, _JIRA_CATEGORY_MAP.get(category))
        if column is not None and column.id != item.status_column_id:
            await self._move_item.execute(
                workspace_id=integration.workspace_id,
                item_id=item.id,
                target_column_id=column.id,
                target_index=10**6,
            )
        return True


def _find_column(board: Any, category: StatusCategory | None) -> Any:
    if category is None:
        return None
    for column in sorted(board.columns, key=lambda column: column.position):
        if column.category is category:
            return column
    return None
