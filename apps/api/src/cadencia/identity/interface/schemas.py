"""Schemas HTTP do contexto identity."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from cadencia.identity.domain.value_objects import DEFAULT_TIMEZONE, Role

PASSWORD_MIN_LENGTH = 10


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)
    locale: str = Field(default="pt-BR", max_length=10)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    locale: str


class SessionOut(BaseModel):
    access_token: str
    access_expires_at: datetime
    user: UserOut


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    timezone: str
    role: Role


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(default=DEFAULT_TIMEZONE, max_length=64)


class MemberOut(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    role: Role
    joined_at: datetime


class InviteRequest(BaseModel):
    email: EmailStr
    role: Role = Role.MEMBER


class InviteOut(BaseModel):
    invite_id: uuid.UUID
    token: str
    expires_at: datetime


class AcceptInviteOut(BaseModel):
    workspace: WorkspaceOut
