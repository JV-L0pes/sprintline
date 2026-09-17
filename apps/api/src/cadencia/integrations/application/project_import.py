"""Helper compartilhado de importação: garante o projeto interno de destino.

O vinculo externo -> interno fica em `external_mappings` (entity_type="project"),
garantindo idempotência entre chunks e entre Jira/Trello.
"""

from __future__ import annotations

import re
import uuid

from cadencia.integrations.domain.repositories import ExternalMappingRepository
from cadencia.shared.errors import NotFoundError
from cadencia.work.application.use_cases import CreateProject
from cadencia.work.domain.entities import Board, Project
from cadencia.work.domain.repositories import BoardRepository, ProjectRepository

_KEY_SANITIZE = re.compile(r"[^A-Za-z0-9]")


def project_key_from_name(name: str) -> str:
    """Deriva uma chave válida (^[A-Z][A-Z0-9]{1,9}$) a partir do nome externo."""
    key = _KEY_SANITIZE.sub("", name).upper()[:10]
    if len(key) < 2:
        key = f"T{key}".ljust(2, "X")
    if not key[0].isalpha():
        key = f"T{key}"[:10]
    return key


async def _unique_key(projects: ProjectRepository, workspace_id: uuid.UUID, preferred: str) -> str:
    existing = {project.key for project in await projects.list_for_workspace(workspace_id)}
    base = project_key_from_name(preferred)
    candidate = base
    suffix = 1
    while candidate in existing:
        suffix += 1
        candidate = f"{base[: 10 - len(str(suffix))]}{suffix}"
    return candidate


async def ensure_import_project(
    *,
    projects: ProjectRepository,
    boards: BoardRepository,
    create_project: CreateProject,
    mappings: ExternalMappingRepository,
    connection_id: uuid.UUID,
    workspace_id: uuid.UUID,
    external_id: str,
    name: str,
    preferred_key: str,
) -> tuple[Project, Board]:
    mapped = await mappings.find(connection_id, "project", external_id)
    if mapped is not None:
        project = await projects.get(mapped, workspace_id)
        if project is not None:
            board = await boards.get_by_project(project.id)
            if board is not None:
                return project, board

    key = await _unique_key(projects, workspace_id, preferred_key)
    view = await create_project.execute(workspace_id=workspace_id, name=name, key=key)
    await mappings.save(connection_id, "project", external_id, view.id)

    project = await projects.get(view.id, workspace_id)
    if project is None:
        raise NotFoundError("Projeto interno não encontrado", code="PROJECT_NOT_FOUND")
    board = await _board_or_raise(boards, view.id)
    return project, board


async def _board_or_raise(boards: BoardRepository, project_id: uuid.UUID) -> Board:
    board = await boards.get_by_project(project_id)
    if board is None:
        raise NotFoundError("Board interno não encontrado", code="BOARD_NOT_FOUND")
    return board
