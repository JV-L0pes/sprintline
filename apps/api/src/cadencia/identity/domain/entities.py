"""Agregados do contexto identity: User, Organization, Workspace, Membership, Invite, Session."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from cadencia.identity.domain.value_objects import (
    DEFAULT_TIMEZONE,
    DEFAULT_WORKING_DAYS,
    Role,
    normalize_email,
    slugify,
    validate_timezone,
    validate_working_days,
)
from cadencia.shared.domain import AggregateRoot, DomainEvent
from cadencia.shared.errors import ConflictError, ForbiddenError, UnauthorizedError, ValidationError
from cadencia.shared.ids import uuid7

INVITE_TTL_DAYS = 7


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    event_type = "user.registered"
    email: str


class User(AggregateRoot):
    def __init__(
        self,
        *,
        email: str,
        name: str,
        password_hash: str,
        locale: str = "pt-BR",
        created_at: datetime,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        if not name.strip():
            raise ValidationError("Nome e obrigatório", code="INVALID_NAME")
        self.email = normalize_email(email)
        self.name = name.strip()[:120]
        self.password_hash = password_hash
        self.locale = locale
        self.created_at = created_at

    @classmethod
    def register(
        cls,
        *,
        email: str,
        name: str,
        password_hash: str,
        locale: str,
        now: datetime,
    ) -> User:
        user = cls(
            email=email,
            name=name,
            password_hash=password_hash,
            locale=locale,
            created_at=now,
        )
        user._record(UserRegistered(email=user.email))
        return user

    def set_password_hash(self, password_hash: str) -> None:
        self.password_hash = password_hash


@dataclass(frozen=True)
class WorkspaceCreated(DomainEvent):
    event_type = "workspace.created"
    name: str
    slug: str


class Organization(AggregateRoot):
    def __init__(
        self,
        *,
        name: str,
        slug: str,
        created_at: datetime,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.name = name.strip()
        self.slug = slug
        self.created_at = created_at


class Workspace(AggregateRoot):
    def __init__(
        self,
        *,
        organization_id: uuid.UUID,
        name: str,
        slug: str,
        timezone: str = DEFAULT_TIMEZONE,
        working_days: tuple[int, ...] = DEFAULT_WORKING_DAYS,
        created_at: datetime,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        if not name.strip():
            raise ValidationError("Nome do workspace e obrigatório", code="INVALID_NAME")
        self.organization_id = organization_id
        self.name = name.strip()[:120]
        self.slug = slug
        self.timezone = validate_timezone(timezone)
        self.working_days = validate_working_days(working_days)
        self.created_at = created_at

    @classmethod
    def create(
        cls,
        *,
        organization_id: uuid.UUID,
        name: str,
        timezone: str,
        now: datetime,
    ) -> Workspace:
        workspace = cls(
            organization_id=organization_id,
            name=name,
            slug=slugify(name),
            timezone=timezone,
            created_at=now,
        )
        workspace._record(WorkspaceCreated(name=workspace.name, slug=workspace.slug))
        return workspace


@dataclass(frozen=True)
class MemberJoined(DomainEvent):
    event_type = "member.joined"
    user_id: uuid.UUID
    role: Role


class Membership(AggregateRoot):
    def __init__(
        self,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        role: Role,
        created_at: datetime,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.role = role
        self.created_at = created_at

    @classmethod
    def join(
        cls,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        role: Role,
        now: datetime,
    ) -> Membership:
        membership = cls(workspace_id=workspace_id, user_id=user_id, role=role, created_at=now)
        membership._record(MemberJoined(user_id=user_id, role=role))
        return membership

    def change_role(self, new_role: Role) -> None:
        self.role = new_role


@dataclass(frozen=True)
class MemberInvited(DomainEvent):
    event_type = "member.invited"
    email: str
    role: Role


@dataclass(frozen=True)
class InviteAccepted(DomainEvent):
    event_type = "invite.accepted"
    email: str


class Invite(AggregateRoot):
    def __init__(
        self,
        *,
        workspace_id: uuid.UUID,
        email: str,
        role: Role,
        token_hash: str,
        expires_at: datetime,
        created_at: datetime,
        accepted_at: datetime | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.workspace_id = workspace_id
        self.email = normalize_email(email)
        self.role = role
        self.token_hash = token_hash
        self.expires_at = expires_at
        self.created_at = created_at
        self.accepted_at = accepted_at

    @classmethod
    def issue(
        cls,
        *,
        workspace_id: uuid.UUID,
        email: str,
        role: Role,
        raw_token: str,
        now: datetime,
    ) -> Invite:
        invite = cls(
            workspace_id=workspace_id,
            email=email,
            role=role,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=now + timedelta(days=INVITE_TTL_DAYS),
            created_at=now,
        )
        invite._record(MemberInvited(email=invite.email, role=role))
        return invite

    def is_open(self, now: datetime) -> bool:
        return self.accepted_at is None and self.expires_at > now

    def validate_for(self, *, user_email: str, now: datetime) -> None:
        """Mesmas checagens do accept, sem consumir o convite."""
        if self.accepted_at is not None:
            raise ConflictError("Convite já utilizado", code="INVITE_ALREADY_USED")
        if self.expires_at <= now:
            raise ConflictError("Convite expirado", code="INVITE_EXPIRED")
        if normalize_email(user_email) != self.email:
            raise ForbiddenError("Convite emitido para outro email", code="INVITE_EMAIL_MISMATCH")

    def accept(self, *, user_email: str, now: datetime) -> None:
        self.validate_for(user_email=user_email, now=now)
        self.accepted_at = now
        self._record(InviteAccepted(email=self.email))


class Session(AggregateRoot):
    def __init__(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        family_id: uuid.UUID,
        expires_at: datetime,
        created_at: datetime,
        revoked_at: datetime | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.user_id = user_id
        self.token_hash = token_hash
        self.family_id = family_id
        self.expires_at = expires_at
        self.created_at = created_at
        self.revoked_at = revoked_at

    @classmethod
    def issue(
        cls,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        family_id: uuid.UUID,
        ttl_days: int,
        now: datetime,
    ) -> Session:
        return cls(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=now + timedelta(days=ttl_days),
            created_at=now,
        )

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def ensure_active(self, now: datetime) -> None:
        if self.is_revoked:
            raise UnauthorizedError("Sessão revogada", code="SESSION_REVOKED")
        if self.expires_at <= now:
            raise UnauthorizedError("Sessão expirada", code="SESSION_EXPIRED")

    def revoke(self, now: datetime) -> None:
        self.revoked_at = now


def new_family_id() -> uuid.UUID:
    return uuid7()
