"""Mapeamento relacional do contexto identity."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from cadencia.platform.db import Base


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(sa.String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(sa.String(120))
    password_hash: Mapped[str] = mapped_column(sa.String(256))
    locale: Mapped[str] = mapped_column(sa.String(10), default="pt-BR")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))


class OrganizationRow(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(120))
    slug: Mapped[str] = mapped_column(sa.String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))


class WorkspaceRow(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(sa.String(120))
    slug: Mapped[str] = mapped_column(sa.String(64), unique=True)
    timezone: Mapped[str] = mapped_column(sa.String(64), default="America/Sao_Paulo")
    working_days: Mapped[str] = mapped_column(sa.String(20), default="0,1,2,3,4")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))


class MembershipRow(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_memberships_workspace_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(sa.String(16))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))


class InviteRow(Base):
    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(sa.String(320), index=True)
    role: Mapped[str] = mapped_column(sa.String(16))
    token_hash: Mapped[str] = mapped_column(sa.String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), default=None)


class SessionRow(Base):
    __tablename__ = "refresh_sessions"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(sa.String(128), unique=True, index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), index=True)
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), default=None)
