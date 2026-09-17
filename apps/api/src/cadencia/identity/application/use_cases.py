"""Casos de uso do contexto identity."""

from __future__ import annotations

import uuid

from cadencia.identity.application.dto import (
    InviteView,
    MemberView,
    SessionView,
    TokenPair,
    UserView,
    WorkspaceView,
)
from cadencia.identity.application.ports import PasswordHasher, TokenIssuer
from cadencia.identity.domain.entities import (
    Invite,
    Membership,
    Organization,
    Session,
    User,
    Workspace,
    new_family_id,
)
from cadencia.identity.domain.repositories import (
    InviteRepository,
    MembershipRepository,
    MembershipWithUser,
    OrganizationRepository,
    SessionRepository,
    UserRepository,
    WorkspaceRepository,
    WorkspaceWithRole,
)
from cadencia.identity.domain.value_objects import (
    PASSWORD_MIN_LENGTH,
    Role,
    role_at_least,
    slugify,
)
from cadencia.shared.clock import Clock
from cadencia.shared.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


def user_view(user: User) -> UserView:
    return UserView(id=user.id, email=user.email, name=user.name, locale=user.locale)


def workspace_view(workspace: Workspace, role: Role) -> WorkspaceView:
    return WorkspaceView(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        timezone=workspace.timezone,
        role=role,
    )


def member_view(entry: MembershipWithUser) -> MemberView:
    return MemberView(
        user_id=entry.user.id,
        name=entry.user.name,
        email=entry.user.email,
        role=entry.membership.role,
        joined_at=entry.membership.created_at,
    )


class RegisterUser:
    def __init__(self, users: UserRepository, hasher: PasswordHasher, clock: Clock) -> None:
        self._users = users
        self._hasher = hasher
        self._clock = clock

    async def execute(self, *, email: str, name: str, password: str, locale: str) -> User:
        if len(password) < PASSWORD_MIN_LENGTH:
            raise ValidationError(
                f"Senha deve ter ao menos {PASSWORD_MIN_LENGTH} caracteres",
                code="WEAK_PASSWORD",
            )
        if await self._users.find_by_email(email.strip().lower()) is not None:
            raise ConflictError("Email já cadastrado", code="EMAIL_ALREADY_REGISTERED")
        user = User.register(
            email=email,
            name=name,
            password_hash=self._hasher.hash(password),
            locale=locale,
            now=self._clock.now(),
        )
        await self._users.add(user)
        return user


class AuthenticateUser:
    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    async def execute(self, *, email: str, password: str) -> User:
        user = await self._users.find_by_email(email.strip().lower())
        if user is None or not self._hasher.verify(user.password_hash, password):
            raise UnauthorizedError("Credenciais inválidas", code="INVALID_CREDENTIALS")
        return user


class StartSession:
    def __init__(self, sessions: SessionRepository, tokens: TokenIssuer, clock: Clock) -> None:
        self._sessions = sessions
        self._tokens = tokens
        self._clock = clock

    async def execute(self, user: User) -> SessionView:
        now = self._clock.now()
        access_token, access_expires_at = self._tokens.create_access(user.id, now)
        raw_refresh = self._tokens.generate_opaque_token()
        ttl = self._tokens.refresh_ttl()
        session = Session.issue(
            user_id=user.id,
            token_hash=self._tokens.hash_opaque_token(raw_refresh),
            family_id=new_family_id(),
            ttl_days=int(ttl.days),
            now=now,
        )
        await self._sessions.add(session)
        return SessionView(
            user=user_view(user),
            tokens=TokenPair(
                access_token=access_token,
                access_expires_at=access_expires_at,
                refresh_token=raw_refresh,
                refresh_expires_at=session.expires_at,
            ),
        )


class RotateSession:
    def __init__(
        self,
        sessions: SessionRepository,
        users: UserRepository,
        tokens: TokenIssuer,
        clock: Clock,
    ) -> None:
        self._sessions = sessions
        self._users = users
        self._tokens = tokens
        self._clock = clock

    async def execute(self, raw_refresh: str) -> SessionView:
        now = self._clock.now()
        token_hash = self._tokens.hash_opaque_token(raw_refresh)
        session = await self._sessions.find_by_token_hash(token_hash)
        if session is None:
            raise UnauthorizedError("Sessão inválida", code="SESSION_NOT_FOUND")
        if session.is_revoked:
            await self._sessions.revoke_family(session.family_id, now)
            raise UnauthorizedError(
                "Reuso de token detectado; sessão revogada", code="SESSION_REUSE_DETECTED"
            )
        session.ensure_active(now)
        session.revoke(now)
        await self._sessions.save(session)

        user = await self._users.get(session.user_id)
        if user is None:
            raise UnauthorizedError("Usuário não encontrado", code="SESSION_USER_MISSING")

        access_token, access_expires_at = self._tokens.create_access(user.id, now)
        raw_new = self._tokens.generate_opaque_token()
        ttl_days = int(self._tokens.refresh_ttl().days)
        new_session = Session.issue(
            user_id=user.id,
            token_hash=self._tokens.hash_opaque_token(raw_new),
            family_id=session.family_id,
            ttl_days=ttl_days,
            now=now,
        )
        await self._sessions.add(new_session)
        return SessionView(
            user=user_view(user),
            tokens=TokenPair(
                access_token=access_token,
                access_expires_at=access_expires_at,
                refresh_token=raw_new,
                refresh_expires_at=new_session.expires_at,
            ),
        )


class EndSession:
    def __init__(self, sessions: SessionRepository, tokens: TokenIssuer, clock: Clock) -> None:
        self._sessions = sessions
        self._tokens = tokens
        self._clock = clock

    async def execute(self, raw_refresh: str) -> None:
        session = await self._sessions.find_by_token_hash(
            self._tokens.hash_opaque_token(raw_refresh)
        )
        if session is not None:
            await self._sessions.revoke_family(session.family_id, self._clock.now())


class CreateWorkspace:
    def __init__(
        self,
        organizations: OrganizationRepository,
        workspaces: WorkspaceRepository,
        memberships: MembershipRepository,
        clock: Clock,
    ) -> None:
        self._organizations = organizations
        self._workspaces = workspaces
        self._memberships = memberships
        self._clock = clock

    async def execute(self, *, user: User, name: str, timezone: str) -> WorkspaceView:
        now = self._clock.now()
        organization = Organization(name=name, slug=slugify(name), created_at=now)
        await self._organizations.add(organization)
        workspace = Workspace.create(
            organization_id=organization.id, name=name, timezone=timezone, now=now
        )
        if await self._workspaces.find_by_slug(workspace.slug) is not None:
            raise ConflictError("Já existe um workspace com este nome", code="WORKSPACE_EXISTS")
        await self._workspaces.add(workspace)
        membership = Membership.join(
            workspace_id=workspace.id, user_id=user.id, role=Role.OWNER, now=now
        )
        await self._memberships.add(membership)
        return workspace_view(workspace, Role.OWNER)


class ListWorkspaces:
    def __init__(self, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    async def execute(self, user_id: uuid.UUID) -> list[WorkspaceView]:
        entries: list[WorkspaceWithRole] = await self._workspaces.list_for_user(user_id)
        return [workspace_view(entry.workspace, entry.role) for entry in entries]


class ListMembers:
    def __init__(self, memberships: MembershipRepository) -> None:
        self._memberships = memberships

    async def execute(self, workspace_id: uuid.UUID) -> list[MemberView]:
        entries = await self._memberships.list_for_workspace(workspace_id)
        return [member_view(entry) for entry in entries]


class InviteMember:
    def __init__(
        self,
        invites: InviteRepository,
        memberships: MembershipRepository,
        users: UserRepository,
        tokens: TokenIssuer,
        clock: Clock,
    ) -> None:
        self._invites = invites
        self._memberships = memberships
        self._users = users
        self._tokens = tokens
        self._clock = clock

    async def execute(
        self,
        *,
        actor_role: Role,
        workspace_id: uuid.UUID,
        email: str,
        role: Role,
    ) -> InviteView:
        if not role_at_least(actor_role, role):
            raise ForbiddenError(
                "Não e possível convidar com papel superior ao seu", code="ROLE_ESCALATION"
            )
        existing_user = await self._users.find_by_email(email.strip().lower())
        if existing_user is not None:
            membership = await self._memberships.get(workspace_id, existing_user.id)
            if membership is not None:
                raise ConflictError("Usuário já é membro do workspace", code="ALREADY_MEMBER")
        now = self._clock.now()
        raw_token = self._tokens.generate_opaque_token()
        invite = Invite.issue(
            workspace_id=workspace_id, email=email, role=role, raw_token=raw_token, now=now
        )
        await self._invites.add(invite)
        return InviteView(invite_id=invite.id, token=raw_token, expires_at=invite.expires_at)


class AcceptInvite:
    def __init__(
        self,
        invites: InviteRepository,
        memberships: MembershipRepository,
        workspaces: WorkspaceRepository,
        tokens: TokenIssuer,
        clock: Clock,
    ) -> None:
        self._invites = invites
        self._memberships = memberships
        self._workspaces = workspaces
        self._tokens = tokens
        self._clock = clock

    async def execute(self, *, token: str, user: User) -> WorkspaceView:
        now = self._clock.now()
        invite = await self._invites.find_by_token_hash(self._tokens.hash_opaque_token(token))
        if invite is None:
            raise NotFoundError("Convite não encontrado", code="INVITE_NOT_FOUND")
        existing = await self._memberships.get(invite.workspace_id, user.id)
        workspace = await self._workspaces.get(invite.workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace não encontrado", code="WORKSPACE_NOT_FOUND")
        if existing is not None:
            # Idempotente: já é membro (ex.: refresh da pagina de convite).
            return workspace_view(workspace, existing.role)
        invite.accept(user_email=user.email, now=now)
        membership = Membership.join(
            workspace_id=invite.workspace_id, user_id=user.id, role=invite.role, now=now
        )
        await self._memberships.add(membership)
        await self._invites.save(invite)
        return workspace_view(workspace, invite.role)


def _ensure_can_manage(*, actor_role: Role, target_role: Role) -> None:
    """Ninguem gerencia alguem com papel igual ou superior ao seu."""
    from cadencia.identity.domain.value_objects import ROLE_RANK

    if ROLE_RANK[target_role] >= ROLE_RANK[actor_role]:
        raise ForbiddenError(
            "Seu papel não permite gerenciar este membro", code="CANNOT_MANAGE_MEMBER"
        )


def _ensure_role_allowed(*, actor_role: Role, new_role: Role) -> None:
    if not role_at_least(actor_role, new_role):
        raise ForbiddenError(
            "Não e possível atribuir papel superior ao seu", code="ROLE_ESCALATION"
        )


async def _owners_count(memberships: MembershipRepository, workspace_id: uuid.UUID) -> int:
    members = await memberships.list_for_workspace(workspace_id)
    return sum(1 for entry in members if entry.membership.role is Role.OWNER)


class ChangeMemberRole:
    def __init__(self, memberships: MembershipRepository, users: UserRepository) -> None:
        self._memberships = memberships
        self._users = users

    async def execute(
        self,
        *,
        actor_id: uuid.UUID,
        actor_role: Role,
        workspace_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: Role,
    ) -> MemberView:
        if target_user_id == actor_id:
            raise ConflictError(
                "Você não pode alterar seu próprio papel", code="CANNOT_MANAGE_SELF"
            )
        target = await self._memberships.get(workspace_id, target_user_id)
        if target is None:
            raise NotFoundError("Membro não encontrado", code="MEMBER_NOT_FOUND")
        _ensure_can_manage(actor_role=actor_role, target_role=target.role)
        _ensure_role_allowed(actor_role=actor_role, new_role=new_role)
        if (
            target.role is Role.OWNER
            and new_role is not Role.OWNER
            and await _owners_count(self._memberships, workspace_id) <= 1
        ):
            raise ConflictError("O workspace precisa de pelo menos um owner", code="LAST_OWNER")
        target.change_role(new_role)
        await self._memberships.save(target)
        user = await self._users.get(target_user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado", code="USER_NOT_FOUND")
        return member_view(MembershipWithUser(membership=target, user=user))


class RemoveMember:
    def __init__(self, memberships: MembershipRepository) -> None:
        self._memberships = memberships

    async def execute(
        self,
        *,
        actor_role: Role,
        actor_id: uuid.UUID,
        workspace_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        if target_user_id == actor_id:
            raise ConflictError("Você não pode remover a si mesmo", code="CANNOT_MANAGE_SELF")
        target = await self._memberships.get(workspace_id, target_user_id)
        if target is None:
            raise NotFoundError("Membro não encontrado", code="MEMBER_NOT_FOUND")
        _ensure_can_manage(actor_role=actor_role, target_role=target.role)
        if target.role is Role.OWNER and await _owners_count(self._memberships, workspace_id) <= 1:
            raise ConflictError("O workspace precisa de pelo menos um owner", code="LAST_OWNER")
        await self._memberships.remove(target)


class ResetMemberPassword:
    def __init__(
        self,
        memberships: MembershipRepository,
        users: UserRepository,
        sessions: SessionRepository,
        hasher: PasswordHasher,
        clock: Clock,
    ) -> None:
        self._memberships = memberships
        self._users = users
        self._sessions = sessions
        self._hasher = hasher
        self._clock = clock

    async def execute(
        self,
        *,
        actor_role: Role,
        workspace_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_password: str,
    ) -> None:
        if len(new_password) < PASSWORD_MIN_LENGTH:
            raise ValidationError(
                f"Senha deve ter ao menos {PASSWORD_MIN_LENGTH} caracteres",
                code="WEAK_PASSWORD",
            )
        target = await self._memberships.get(workspace_id, target_user_id)
        if target is None:
            raise NotFoundError("Membro não encontrado", code="MEMBER_NOT_FOUND")
        _ensure_can_manage(actor_role=actor_role, target_role=target.role)
        user = await self._users.get(target_user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado", code="USER_NOT_FOUND")
        user.set_password_hash(self._hasher.hash(new_password))
        await self._users.save(user)
        await self._sessions.revoke_all_for_user(user.id, self._clock.now())


class ChangeOwnPassword:
    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        hasher: PasswordHasher,
        clock: Clock,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._hasher = hasher
        self._clock = clock

    async def execute(self, *, user: User, current_password: str, new_password: str) -> None:
        if not self._hasher.verify(user.password_hash, current_password):
            raise UnauthorizedError("Senha atual incorreta", code="INVALID_CURRENT_PASSWORD")
        if len(new_password) < PASSWORD_MIN_LENGTH:
            raise ValidationError(
                f"Senha deve ter ao menos {PASSWORD_MIN_LENGTH} caracteres",
                code="WEAK_PASSWORD",
            )
        user.set_password_hash(self._hasher.hash(new_password))
        await self._users.save(user)
        # Toda a família de sessões e revogada: re-login em todos os dispositivos.
        await self._sessions.revoke_all_for_user(user.id, self._clock.now())
