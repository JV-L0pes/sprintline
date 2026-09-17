"""Casos de uso do conector Trello.

Autenticacao: API key do app (server-side) + token gerado pelo fluxo
`/1/authorize` com `response_type=token` — o token volta no fragmento da URL
de retorno e o frontend o entrega via `POST .../trello/connect`.
"""

from __future__ import annotations

import re
import uuid
from datetime import timedelta
from typing import Any

from cadencia.integrations.application.dto import (
    IntegrationView,
    SyncJobView,
    TrelloBoardView,
)
from cadencia.integrations.application.project_import import ensure_import_project
from cadencia.integrations.application.use_cases import (
    integration_view,
    job_view,
    snap_story_points,
)
from cadencia.integrations.domain.entities import Integration, SyncCursor, SyncJob
from cadencia.integrations.domain.ports import TrelloGateway
from cadencia.integrations.domain.repositories import (
    ExternalMappingRepository,
    IntegrationRepository,
    SyncJobRepository,
    TokenStore,
    WebhookEventRepository,
)
from cadencia.platform.config import Settings
from cadencia.platform.security import webhook_token
from cadencia.shared.clock import Clock
from cadencia.shared.errors import NotFoundError, ValidationError
from cadencia.work.application.use_cases import CreateProject, CreateWorkItem, MoveWorkItem
from cadencia.work.domain.repositories import BoardRepository, ProjectRepository
from cadencia.work.domain.value_objects import StatusCategory, WorkItemType

TRELLO_PROVIDER = "TRELLO"
_TOKEN_TTL_DAYS = 3650  # expiracao "never" no authorize do Trello

_POINTS_RE = re.compile(r"[\(\[]\s*(\d{1,3})\s*[\)\]]\s*$")
_DONE_HINTS = ("done", "conclu", "feito", "finaliz", "complete", "deploy", "produ")
_DOING_HINTS = ("progress", "doing", "andamento", "review", "revis", "qa", "test", "homolog", "wip")


def parse_points_from_name(name: str) -> int | None:
    """Story points no Trello nao sao nativos: le `(5)` ou `[5]` no fim do nome."""
    match = _POINTS_RE.search(name.strip())
    if match is None:
        return None
    return snap_story_points(float(match.group(1)))


def category_for_list(name: str) -> StatusCategory:
    """Heuristica de nome de lista -> categoria (override manual fica no board)."""
    lowered = name.lower()
    if any(hint in lowered for hint in _DONE_HINTS):
        return StatusCategory.DONE
    if any(hint in lowered for hint in _DOING_HINTS):
        return StatusCategory.IN_PROGRESS
    return StatusCategory.TODO


def item_type_for_labels(labels: tuple[str, ...]) -> WorkItemType:
    lowered = {label.lower() for label in labels}
    if "bug" in lowered:
        return WorkItemType.BUG
    if "epic" in lowered:
        return WorkItemType.EPIC
    if lowered & {"story", "historia", "história"}:
        return WorkItemType.STORY
    return WorkItemType.TASK


async def access_token_for(tokens: TokenStore, integration: Integration) -> str:
    stored = await tokens.load(integration.id)
    if stored is None or not stored.access_token:
        raise NotFoundError(
            "Token da integracao nao encontrado; reconecte o Trello", code="TOKENS_MISSING"
        )
    return stored.access_token


class StartTrelloAuthorize:
    def __init__(self, gateway: TrelloGateway, settings: Settings) -> None:
        self._gateway = gateway
        self._settings = settings

    async def execute(self) -> str:
        if not self._settings.trello_api_key:
            raise ValidationError(
                "TRELLO_API_KEY nao configurada no servidor", code="TRELLO_NOT_CONFIGURED"
            )
        return self._gateway.build_authorize_url(self._settings.trello_return_url)


class ConnectTrello:
    def __init__(
        self,
        gateway: TrelloGateway,
        connections: IntegrationRepository,
        tokens: TokenStore,
        clock: Clock,
    ) -> None:
        self._gateway = gateway
        self._connections = connections
        self._tokens = tokens
        self._clock = clock

    async def execute(self, *, workspace_id: uuid.UUID, token: str) -> IntegrationView:
        cleaned = token.strip()
        if not cleaned:
            raise ValidationError("Token do Trello vazio", code="INVALID_TRELLO_TOKEN")
        member = await self._gateway.member_me(cleaned)
        now = self._clock.now()
        existing = next(
            (
                integration
                for integration in await self._connections.list_for_workspace(workspace_id)
                if integration.provider == TRELLO_PROVIDER and integration.cloud_id == member.id
            ),
            None,
        )
        if existing is not None:
            # Reconexao idempotente: apenas atualiza o token do membro ja conectado.
            await self._tokens.save(
                existing.id,
                access_token=cleaned,
                refresh_token="",
                access_expires_at=now + timedelta(days=_TOKEN_TTL_DAYS),
            )
            return integration_view(existing)
        integration = Integration.connect(
            workspace_id=workspace_id,
            provider=TRELLO_PROVIDER,
            cloud_id=member.id,
            site_url=f"https://trello.com/{member.username}",
            now=now,
        )
        await self._connections.add(integration)
        await self._tokens.save(
            integration.id,
            access_token=cleaned,
            refresh_token="",
            access_expires_at=now + timedelta(days=_TOKEN_TTL_DAYS),
        )
        return integration_view(integration)


class ListTrelloBoards:
    def __init__(
        self,
        gateway: TrelloGateway,
        connections: IntegrationRepository,
        tokens: TokenStore,
    ) -> None:
        self._gateway = gateway
        self._connections = connections
        self._tokens = tokens

    async def execute(
        self, *, workspace_id: uuid.UUID, connection_id: uuid.UUID
    ) -> list[TrelloBoardView]:
        integration = await self._connections.get(connection_id, workspace_id)
        if integration is None or integration.provider != TRELLO_PROVIDER:
            raise NotFoundError("Integracao nao encontrada", code="INTEGRATION_NOT_FOUND")
        token = await access_token_for(self._tokens, integration)
        boards = await self._gateway.member_boards(token)
        return [
            TrelloBoardView(id=board.id, name=board.name, url=board.url, closed=board.closed)
            for board in boards
            if not board.closed
        ]


class StartTrelloImport:
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
        self, *, workspace_id: uuid.UUID, connection_id: uuid.UUID, board_id: str
    ) -> SyncJobView:
        integration = await self._connections.get(connection_id, workspace_id)
        if integration is None or integration.provider != TRELLO_PROVIDER:
            raise NotFoundError("Integracao nao encontrada", code="INTEGRATION_NOT_FOUND")
        job = SyncJob(
            connection_id=integration.id,
            job_type="IMPORT_PROJECT",
            state="PENDING",
            cursor=SyncCursor(project_key=board_id, start_at=0, board_id=board_id),
            created_at=self._clock.now(),
        )
        await self._jobs.add(job)
        return job_view(job)


class RunTrelloImportChunk:
    """Importa cards do board em lotes idempotentes (RN-20)."""

    def __init__(
        self,
        connections: IntegrationRepository,
        jobs: SyncJobRepository,
        mappings: ExternalMappingRepository,
        tokens: TokenStore,
        gateway: TrelloGateway,
        projects: ProjectRepository,
        boards: BoardRepository,
        create_item: CreateWorkItem,
        move_item: MoveWorkItem,
        settings: Settings,
        clock: Clock,
    ) -> None:
        self._connections = connections
        self._jobs = jobs
        self._mappings = mappings
        self._tokens = tokens
        self._gateway = gateway
        self._projects = projects
        self._boards = boards
        self._create_item = create_item
        self._move_item = move_item
        self._settings = settings
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
        if integration is None or integration.provider != TRELLO_PROVIDER:
            raise NotFoundError("Integracao nao encontrada", code="INTEGRATION_NOT_FOUND")
        job = await self._jobs.get(job_id)
        if job is None or job.connection_id != integration.id:
            raise NotFoundError("Job de importacao nao encontrado", code="JOB_NOT_FOUND")
        now = self._clock.now()
        job.mark_running(now)
        token = await access_token_for(self._tokens, integration)
        board_id = job.cursor.board_id or job.cursor.project_key
        external_board = await self._gateway.get_board(token, board_id)
        if external_board is None:
            raise NotFoundError("Board do Trello nao encontrado", code="BOARD_NOT_FOUND")

        project, internal_board = await ensure_import_project(
            projects=self._projects,
            boards=self._boards,
            create_project=CreateProject(
                projects=self._projects, boards=self._boards, clock=self._clock
            ),
            mappings=self._mappings,
            connection_id=integration.id,
            workspace_id=workspace_id,
            external_id=board_id,
            name=f"{external_board.name} (Trello)",
            preferred_key=external_board.name,
        )
        column_by_category = {
            column.category: column.id
            for column in sorted(internal_board.columns, key=lambda column: column.position)
        }

        lists = await self._gateway.board_lists(token, board_id)
        for trello_list in lists:
            category = category_for_list(trello_list.name)
            column_id = column_by_category.get(category)
            if column_id is not None:
                await self._mappings.save(integration.id, "list", trello_list.id, column_id)

        cards = [
            card for card in await self._gateway.board_cards(token, board_id) if not card.closed
        ]
        window = cards[job.cursor.start_at : job.cursor.start_at + limit]
        imported = 0
        for card in window:
            if await self._mappings.find(integration.id, "card", card.id) is not None:
                continue
            item_type = item_type_for_labels(card.labels)
            view = await self._create_item.execute(
                workspace_id=workspace_id,
                project_id=project.id,
                item_type=item_type,
                title=card.name or f"Card {card.id}",
                description=f"Importado do Trello: {card.url}",
                story_points=parse_points_from_name(card.name),
            )
            target_column = await self._mappings.find(integration.id, "list", card.id_list)
            if target_column is not None and target_column != view.status_column_id:
                await self._move_item.execute(
                    workspace_id=workspace_id,
                    item_id=view.id,
                    target_column_id=target_column,
                    target_index=10**6,
                )
            await self._mappings.save(integration.id, "card", card.id, view.id)
            imported += 1

        job.advance(
            imported=imported,
            next_start_at=job.cursor.start_at + len(window),
            has_more=job.cursor.start_at + len(window) < len(cards),
            now=now,
        )
        await self._jobs.save(job)
        if job.state == "DONE":
            await self._register_webhook(integration, token, board_id)
        return job_view(job)

    async def _register_webhook(self, integration: Integration, token: str, board_id: str) -> None:
        callback = (
            f"{self._settings.trello_webhook_base}/{integration.id}"
            f"?token={webhook_token(str(integration.id), self._settings)}"
        )
        try:
            await self._gateway.register_webhook(
                token, board_id, callback, self._settings.trello_app_name
            )
        except Exception:
            return


class HandleTrelloWebhook:
    """Deduplica actions e sincroniza o card correspondente (RN-20)."""

    def __init__(
        self,
        connections: IntegrationRepository,
        webhooks: WebhookEventRepository,
        mappings: ExternalMappingRepository,
        tokens: TokenStore,
        gateway: TrelloGateway,
        move_item: MoveWorkItem,
        clock: Clock,
    ) -> None:
        self._connections = connections
        self._webhooks = webhooks
        self._mappings = mappings
        self._tokens = tokens
        self._gateway = gateway
        self._move_item = move_item
        self._clock = clock

    async def execute(self, *, connection_id: uuid.UUID, payload: dict[str, Any]) -> bool:
        integration = await self._connections.get_by_id(connection_id)
        if integration is None or integration.provider != TRELLO_PROVIDER:
            raise NotFoundError("Integracao nao encontrada", code="INTEGRATION_NOT_FOUND")
        action = payload.get("action") or {}
        action_id = str(action.get("id", ""))
        action_type = str(action.get("type", ""))
        if not action_id:
            return True
        if not await self._webhooks.register(integration.id, action_id, self._clock.now()):
            return False
        if action_type not in {
            "createCard",
            "updateCard",
            "moveCardToBoard",
            "convertToCardFromCheckItem",
        }:
            return True
        card_id = str(((action.get("data") or {}).get("card") or {}).get("id", ""))
        internal_id = (
            await self._mappings.find(integration.id, "card", card_id) if card_id else None
        )
        if internal_id is None:
            return True
        token = await access_token_for(self._tokens, integration)
        card = await self._gateway.get_card(token, card_id)
        if card is None or card.closed:
            return True
        column_id = await self._mappings.find(integration.id, "list", card.id_list)
        if column_id is None:
            return True
        await self._move_item.execute(
            workspace_id=integration.workspace_id,
            item_id=internal_id,
            target_column_id=column_id,
            target_index=10**6,
        )
        return True
