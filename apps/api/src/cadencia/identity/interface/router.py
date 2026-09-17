"""Rotas HTTP de identidade: auth, workspaces, membros e convites."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from cadencia.identity.application.use_cases import (
    AcceptInvite,
    AuthenticateUser,
    ChangeMemberRole,
    ChangeOwnPassword,
    CreateWorkspace,
    EndSession,
    InviteMember,
    ListMembers,
    ListWorkspaces,
    RegisterUser,
    RemoveMember,
    ResetMemberPassword,
    RotateSession,
    StartSession,
)
from cadencia.identity.infrastructure.repositories import (
    SqlInviteRepository,
    SqlMembershipRepository,
    SqlOrganizationRepository,
    SqlSessionRepository,
    SqlUserRepository,
    SqlWorkspaceRepository,
)
from cadencia.identity.interface import schemas
from cadencia.identity.interface.deps import (
    AdminAccessDep,
    CurrentUser,
    SessionDep,
    WorkspaceAccessDep,
    get_clock,
    get_password_hasher,
    get_token_issuer,
)
from cadencia.platform.config import Settings
from cadencia.platform.rate_limit import RateLimiter, client_ip
from cadencia.shared.errors import ForbiddenError, NotFoundError, UnauthorizedError

router = APIRouter(prefix="/api/v1", tags=["identity"])


def _client_ip(request: Request) -> str:
    return client_ip(
        request.headers.get("x-forwarded-for"),
        request.client.host if request.client else None,
    )


def _limiter(session: AsyncSession) -> RateLimiter:
    return RateLimiter(session, get_clock())


def _set_refresh_cookie(
    response: Response, settings: Settings, raw: str, expires: datetime
) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=raw,
        expires=expires,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
    )


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: schemas.RegisterRequest,
    request: Request,
    session: SessionDep,
) -> schemas.UserOut:
    settings = request.app.state.settings
    clock = get_clock()
    await _limiter(session).enforce(
        f"register:ip:{_client_ip(request)}",
        limit=settings.register_max_attempts,
        window_minutes=settings.register_window_minutes,
        label="registro",
    )
    if settings.registration_mode == "closed":
        raise ForbiddenError("Registro desabilitado neste servidor", code="REGISTRATION_CLOSED")

    if payload.invite_token:
        tokens = get_token_issuer(request)
        invite = await SqlInviteRepository(session).find_by_token_hash(
            tokens.hash_opaque_token(payload.invite_token)
        )
        if invite is None:
            raise NotFoundError("Convite nao encontrado", code="INVITE_NOT_FOUND")
        invite.validate_for(user_email=payload.email, now=clock.now())
    elif settings.is_registration_invite_only:
        raise ForbiddenError(
            "Registro somente por convite: peça um link a um admin",
            code="REGISTRATION_INVITE_REQUIRED",
        )

    use_case = RegisterUser(SqlUserRepository(session), get_password_hasher(), clock)
    user = await use_case.execute(
        email=payload.email, name=payload.name, password=payload.password, locale=payload.locale
    )
    return schemas.UserOut(id=user.id, email=user.email, name=user.name, locale=user.locale)


@router.get("/meta")
async def meta(request: Request) -> schemas.MetaOut:
    settings = request.app.state.settings
    return schemas.MetaOut(app_name=settings.app_name, registration_mode=settings.registration_mode)


@router.post("/auth/login")
async def login(
    payload: schemas.LoginRequest,
    response: Response,
    session: SessionDep,
    request: Request,
) -> schemas.SessionOut:
    settings = request.app.state.settings
    limiter = _limiter(session)
    await limiter.enforce(
        f"login:ip:{_client_ip(request)}",
        limit=settings.login_max_attempts,
        window_minutes=settings.login_window_minutes,
        label="login",
    )
    email_key = f"login:email:{payload.email.strip().lower()}"
    await limiter.enforce(
        email_key,
        limit=settings.login_max_attempts,
        window_minutes=settings.login_window_minutes,
        label="login",
    )
    authenticator = AuthenticateUser(SqlUserRepository(session), get_password_hasher())
    user = await authenticator.execute(email=payload.email, password=payload.password)
    await limiter.clear(email_key)
    starter = StartSession(SqlSessionRepository(session), get_token_issuer(request), get_clock())
    session_view = await starter.execute(user)
    _set_refresh_cookie(
        response,
        request.app.state.settings,
        session_view.tokens.refresh_token,
        session_view.tokens.refresh_expires_at,
    )
    return schemas.SessionOut(
        access_token=session_view.tokens.access_token,
        access_expires_at=session_view.tokens.access_expires_at,
        user=schemas.UserOut(id=user.id, email=user.email, name=user.name, locale=user.locale),
    )


@router.post("/auth/refresh")
async def refresh(
    request: Request,
    response: Response,
    session: SessionDep,
) -> schemas.SessionOut:
    settings = request.app.state.settings
    await _limiter(session).enforce(
        f"refresh:ip:{_client_ip(request)}",
        limit=settings.refresh_max_attempts,
        window_minutes=settings.refresh_window_minutes,
        label="refresh",
    )
    raw = request.cookies.get(request.app.state.settings.cookie_name)
    if not raw:
        raise UnauthorizedError("Sessao ausente", code="SESSION_NOT_FOUND")
    rotator = RotateSession(
        SqlSessionRepository(session),
        SqlUserRepository(session),
        get_token_issuer(request),
        get_clock(),
    )
    try:
        session_view = await rotator.execute(raw)
    except UnauthorizedError as exc:
        # Reuse detection revoga a familia antes de falhar: efeito de seguranca
        # precisa ser durável mesmo com o rollback do Unit of Work.
        if exc.code == "SESSION_REUSE_DETECTED":
            await session.commit()
        raise
    _set_refresh_cookie(
        response,
        request.app.state.settings,
        session_view.tokens.refresh_token,
        session_view.tokens.refresh_expires_at,
    )
    return schemas.SessionOut(
        access_token=session_view.tokens.access_token,
        access_expires_at=session_view.tokens.access_expires_at,
        user=schemas.UserOut(
            id=session_view.user.id,
            email=session_view.user.email,
            name=session_view.user.name,
            locale=session_view.user.locale,
        ),
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, session: SessionDep) -> None:
    raw = request.cookies.get(request.app.state.settings.cookie_name)
    if raw:
        await EndSession(
            SqlSessionRepository(session), get_token_issuer(request), get_clock()
        ).execute(raw)
    response.delete_cookie(request.app.state.settings.cookie_name, path="/api/v1/auth")


@router.get("/auth/me")
async def me(user: CurrentUser) -> schemas.UserOut:
    return schemas.UserOut(id=user.id, email=user.email, name=user.name, locale=user.locale)


@router.get("/workspaces")
async def list_workspaces(user: CurrentUser, session: SessionDep) -> list[schemas.WorkspaceOut]:
    views = await ListWorkspaces(SqlWorkspaceRepository(session)).execute(user.id)
    return [
        schemas.WorkspaceOut(
            id=view.id, name=view.name, slug=view.slug, timezone=view.timezone, role=view.role
        )
        for view in views
    ]


@router.post("/workspaces", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: schemas.WorkspaceCreateRequest, user: CurrentUser, session: SessionDep
) -> schemas.WorkspaceOut:
    view = await CreateWorkspace(
        SqlOrganizationRepository(session),
        SqlWorkspaceRepository(session),
        SqlMembershipRepository(session),
        get_clock(),
    ).execute(user=user, name=payload.name, timezone=payload.timezone)
    return schemas.WorkspaceOut(
        id=view.id, name=view.name, slug=view.slug, timezone=view.timezone, role=view.role
    )


@router.get("/workspaces/{workspace_id}")
async def get_workspace(access: WorkspaceAccessDep) -> schemas.WorkspaceOut:
    return schemas.WorkspaceOut(
        id=access.workspace.id,
        name=access.workspace.name,
        slug=access.workspace.slug,
        timezone=access.workspace.timezone,
        role=access.role,
    )


@router.get("/workspaces/{workspace_id}/members")
async def list_members(access: WorkspaceAccessDep, session: SessionDep) -> list[schemas.MemberOut]:
    members = await ListMembers(SqlMembershipRepository(session)).execute(access.workspace.id)
    return [
        schemas.MemberOut(
            user_id=member.user_id,
            name=member.name,
            email=member.email,
            role=member.role,
            joined_at=member.joined_at,
        )
        for member in members
    ]


@router.post(
    "/workspaces/{workspace_id}/invites",
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    workspace_id: uuid.UUID,
    payload: schemas.InviteRequest,
    session: SessionDep,
    request: Request,
    access: AdminAccessDep,
) -> schemas.InviteOut:
    view = await InviteMember(
        SqlInviteRepository(session),
        SqlMembershipRepository(session),
        SqlUserRepository(session),
        get_token_issuer(request),
        get_clock(),
    ).execute(
        actor_role=access.role,
        workspace_id=workspace_id,
        email=payload.email,
        role=payload.role,
    )
    return schemas.InviteOut(invite_id=view.invite_id, token=view.token, expires_at=view.expires_at)


@router.post("/invites/{token}/accept", status_code=status.HTTP_201_CREATED)
async def accept_invite(
    token: str, user: CurrentUser, session: SessionDep, request: Request
) -> schemas.AcceptInviteOut:
    view = await AcceptInvite(
        SqlInviteRepository(session),
        SqlMembershipRepository(session),
        SqlWorkspaceRepository(session),
        get_token_issuer(request),
        get_clock(),
    ).execute(token=token, user=user)
    return schemas.AcceptInviteOut(
        workspace=schemas.WorkspaceOut(
            id=view.id, name=view.name, slug=view.slug, timezone=view.timezone, role=view.role
        )
    )


@router.post("/auth/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(
    payload: schemas.PasswordChangeRequest, user: CurrentUser, session: SessionDep
) -> None:
    await ChangeOwnPassword(
        SqlUserRepository(session),
        SqlSessionRepository(session),
        get_password_hasher(),
        get_clock(),
    ).execute(
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )


@router.patch("/workspaces/{workspace_id}/members/{user_id}")
async def change_member_role(
    user_id: uuid.UUID,
    payload: schemas.MemberRoleUpdateRequest,
    access: AdminAccessDep,
    session: SessionDep,
) -> schemas.MemberOut:
    view = await ChangeMemberRole(
        SqlMembershipRepository(session), SqlUserRepository(session)
    ).execute(
        actor_id=access.user.id,
        actor_role=access.role,
        workspace_id=access.workspace.id,
        target_user_id=user_id,
        new_role=payload.role,
    )
    return schemas.MemberOut(
        user_id=view.user_id,
        name=view.name,
        email=view.email,
        role=view.role,
        joined_at=view.joined_at,
    )


@router.delete(
    "/workspaces/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    user_id: uuid.UUID,
    access: AdminAccessDep,
    session: SessionDep,
) -> None:
    await RemoveMember(SqlMembershipRepository(session)).execute(
        actor_id=access.user.id,
        actor_role=access.role,
        workspace_id=access.workspace.id,
        target_user_id=user_id,
    )


@router.post(
    "/workspaces/{workspace_id}/members/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reset_member_password(
    user_id: uuid.UUID,
    payload: schemas.MemberPasswordRequest,
    access: AdminAccessDep,
    session: SessionDep,
) -> None:
    await ResetMemberPassword(
        SqlMembershipRepository(session),
        SqlUserRepository(session),
        SqlSessionRepository(session),
        get_password_hasher(),
        get_clock(),
    ).execute(
        actor_role=access.role,
        workspace_id=access.workspace.id,
        target_user_id=user_id,
        new_password=payload.new_password,
    )
