"""DTOs de entrada/saida do contexto identity (sem dependencia de framework)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from cadencia.identity.domain.value_objects import Role


@dataclass(frozen=True)
class UserView:
    id: uuid.UUID
    email: str
    name: str
    locale: str


@dataclass(frozen=True)
class WorkspaceView:
    id: uuid.UUID
    name: str
    slug: str
    timezone: str
    role: Role


@dataclass(frozen=True)
class MemberView:
    user_id: uuid.UUID
    name: str
    email: str
    role: Role
    joined_at: datetime


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime


@dataclass(frozen=True)
class SessionView:
    user: UserView
    tokens: TokenPair


@dataclass(frozen=True)
class InviteView:
    invite_id: uuid.UUID
    token: str
    expires_at: datetime
