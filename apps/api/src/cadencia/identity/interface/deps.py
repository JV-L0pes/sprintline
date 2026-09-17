"""Dependencias de autenticacao e tenancy compartilhadas pelos routers."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from cadencia.identity.domain.entities import Membership, User, Workspace
from cadencia.identity.domain.value_objects import Role, role_at_least
from cadencia.identity.infrastructure.repositories import (
    SqlMembershipRepository,
    SqlUserRepository,
    SqlWorkspaceRepository,
)
from cadencia.identity.infrastructure.security import Argon2PasswordHasher, JwtTokenIssuer
from cadencia.platform.db import get_session
from cadencia.platform.security import decode_access_token
from cadencia.shared.clock import Clock, SystemClock
from cadencia.shared.domain import AuditInfo
from cadencia.shared.errors import ForbiddenError, NotFoundError, UnauthorizedError


def get_clock() -> Clock:
    return SystemClock()


def get_password_hasher() -> Argon2PasswordHasher:
    return Argon2PasswordHasher()


def get_token_issuer(request: Request) -> JwtTokenIssuer:
    return JwtTokenIssuer(request.app.state.settings)


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    request: Request,
    session: SessionDep,
) -> User:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise UnauthorizedError("Token de acesso ausente", code="MISSING_TOKEN")
    user_id = decode_access_token(header[7:].strip(), request.app.state.settings)
    user = await SqlUserRepository(session).get(user_id)
    if user is None:
        raise UnauthorizedError("Usuario nao encontrado", code="USER_NOT_FOUND")
    session.info["audit"] = AuditInfo(actor_id=user.id, source="local")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass(frozen=True)
class WorkspaceAccess:
    user: User
    workspace: Workspace
    membership: Membership

    @property
    def role(self) -> Role:
        return self.membership.role


async def get_workspace_access(
    workspace_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
) -> WorkspaceAccess:
    """RN-02: nao-membro recebe 404 (nao 403) para nao vazar existencia."""
    membership = await SqlMembershipRepository(session).get(workspace_id, user.id)
    if membership is None:
        raise NotFoundError("Workspace nao encontrado", code="WORKSPACE_NOT_FOUND")
    workspace = await SqlWorkspaceRepository(session).get(workspace_id)
    if workspace is None:
        raise NotFoundError("Workspace nao encontrado", code="WORKSPACE_NOT_FOUND")
    return WorkspaceAccess(user=user, workspace=workspace, membership=membership)


WorkspaceAccessDep = Annotated[WorkspaceAccess, Depends(get_workspace_access)]


def require_role(
    minimum: Role,
) -> Callable[..., Coroutine[Any, Any, WorkspaceAccess]]:
    async def _check(access: WorkspaceAccessDep) -> WorkspaceAccess:
        if not role_at_least(access.role, minimum):
            raise ForbiddenError("Seu papel nao permite esta operacao", code="INSUFFICIENT_ROLE")
        return access

    return _check


AdminAccessDep = Annotated[WorkspaceAccess, Depends(require_role(Role.ADMIN))]
MemberAccessDep = Annotated[WorkspaceAccess, Depends(require_role(Role.MEMBER))]
