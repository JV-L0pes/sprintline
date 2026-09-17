"""Adaptadores SQLAlchemy das portas de identity."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from cadencia.identity.domain.entities import (
    Invite,
    Membership,
    Organization,
    Session,
    User,
    Workspace,
)
from cadencia.identity.domain.repositories import (
    MembershipWithUser,
    WorkspaceWithRole,
)
from cadencia.identity.domain.value_objects import Role
from cadencia.identity.infrastructure import orm
from cadencia.platform.db import ensure_utc
from cadencia.platform.events import audit_for, clock_for, recorder_for


def _user(row: orm.UserRow) -> User:
    return User(
        entity_id=row.id,
        email=row.email,
        name=row.name,
        password_hash=row.password_hash,
        locale=row.locale,
        created_at=ensure_utc(row.created_at) or row.created_at,
    )


def _workspace(row: orm.WorkspaceRow) -> Workspace:
    return Workspace(
        entity_id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        slug=row.slug,
        timezone=row.timezone,
        working_days=tuple(int(day) for day in row.working_days.split(",") if day != ""),
        created_at=ensure_utc(row.created_at) or row.created_at,
    )


def _membership(row: orm.MembershipRow) -> Membership:
    return Membership(
        entity_id=row.id,
        workspace_id=row.workspace_id,
        user_id=row.user_id,
        role=Role(row.role),
        created_at=ensure_utc(row.created_at) or row.created_at,
    )


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: uuid.UUID) -> User | None:
        row = await self._session.get(orm.UserRow, user_id)
        return _user(row) if row else None

    async def find_by_email(self, email: str) -> User | None:
        row = (
            await self._session.execute(
                sa.select(orm.UserRow).where(orm.UserRow.email == email.strip().lower())
            )
        ).scalar_one_or_none()
        return _user(row) if row else None

    async def add(self, user: User) -> None:
        self._session.add(
            orm.UserRow(
                id=user.id,
                email=user.email,
                name=user.name,
                password_hash=user.password_hash,
                locale=user.locale,
                created_at=user.created_at,
            )
        )
        await self._session.flush()
        recorder_for(self._session).append(
            user,
            workspace_id=None,
            audit=audit_for(self._session),
            occurred_at=clock_for(self._session).now(),
        )

    async def save(self, user: User) -> None:
        row = await self._session.get(orm.UserRow, user.id)
        if row is None:
            await self.add(user)
            return
        row.name = user.name
        row.password_hash = user.password_hash
        row.locale = user.locale
        await self._session.flush()


class SqlOrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, organization: Organization) -> None:
        self._session.add(
            orm.OrganizationRow(
                id=organization.id,
                name=organization.name,
                slug=organization.slug,
                created_at=organization.created_at,
            )
        )
        await self._session.flush()


class SqlWorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, workspace_id: uuid.UUID) -> Workspace | None:
        row = await self._session.get(orm.WorkspaceRow, workspace_id)
        return _workspace(row) if row else None

    async def find_by_slug(self, slug: str) -> Workspace | None:
        row = (
            await self._session.execute(
                sa.select(orm.WorkspaceRow).where(orm.WorkspaceRow.slug == slug)
            )
        ).scalar_one_or_none()
        return _workspace(row) if row else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[WorkspaceWithRole]:
        result = await self._session.execute(
            sa.select(orm.WorkspaceRow, orm.MembershipRow.role)
            .join(orm.MembershipRow, orm.MembershipRow.workspace_id == orm.WorkspaceRow.id)
            .where(orm.MembershipRow.user_id == user_id)
            .order_by(orm.WorkspaceRow.created_at)
        )
        return [
            WorkspaceWithRole(workspace=_workspace(row), role=Role(role))
            for row, role in result.all()
        ]

    async def add(self, workspace: Workspace) -> None:
        self._session.add(
            orm.WorkspaceRow(
                id=workspace.id,
                organization_id=workspace.organization_id,
                name=workspace.name,
                slug=workspace.slug,
                timezone=workspace.timezone,
                working_days=",".join(str(day) for day in workspace.working_days),
                created_at=workspace.created_at,
            )
        )
        await self._session.flush()
        recorder_for(self._session).append(
            workspace,
            workspace_id=workspace.id,
            audit=audit_for(self._session),
            occurred_at=clock_for(self._session).now(),
        )


class SqlMembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Membership | None:
        row = (
            await self._session.execute(
                sa.select(orm.MembershipRow).where(
                    orm.MembershipRow.workspace_id == workspace_id,
                    orm.MembershipRow.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        return _membership(row) if row else None

    async def list_for_workspace(self, workspace_id: uuid.UUID) -> list[MembershipWithUser]:
        result = await self._session.execute(
            sa.select(orm.MembershipRow, orm.UserRow)
            .join(orm.UserRow, orm.UserRow.id == orm.MembershipRow.user_id)
            .where(orm.MembershipRow.workspace_id == workspace_id)
            .order_by(orm.MembershipRow.created_at)
        )
        return [
            MembershipWithUser(membership=_membership(row), user=_user(user_row))
            for row, user_row in result.all()
        ]

    async def add(self, membership: Membership) -> None:
        self._session.add(
            orm.MembershipRow(
                id=membership.id,
                workspace_id=membership.workspace_id,
                user_id=membership.user_id,
                role=membership.role.value,
                created_at=membership.created_at,
            )
        )
        await self._session.flush()
        recorder_for(self._session).append(
            membership,
            workspace_id=membership.workspace_id,
            audit=audit_for(self._session),
            occurred_at=clock_for(self._session).now(),
        )

    async def save(self, membership: Membership) -> None:
        row = await self._session.get(orm.MembershipRow, membership.id)
        if row is not None:
            row.role = membership.role.value
            await self._session.flush()

    async def remove(self, membership: Membership) -> None:
        row = await self._session.get(orm.MembershipRow, membership.id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()


class SqlInviteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_token_hash(self, token_hash: str) -> Invite | None:
        row = (
            await self._session.execute(
                sa.select(orm.InviteRow).where(orm.InviteRow.token_hash == token_hash)
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return Invite(
            entity_id=row.id,
            workspace_id=row.workspace_id,
            email=row.email,
            role=Role(row.role),
            token_hash=row.token_hash,
            expires_at=ensure_utc(row.expires_at) or row.expires_at,
            created_at=ensure_utc(row.created_at) or row.created_at,
            accepted_at=ensure_utc(row.accepted_at),
        )

    def _append_events(self, invite: Invite) -> None:
        recorder_for(self._session).append(
            invite,
            workspace_id=invite.workspace_id,
            audit=audit_for(self._session),
            occurred_at=clock_for(self._session).now(),
        )

    async def add(self, invite: Invite) -> None:
        self._session.add(
            orm.InviteRow(
                id=invite.id,
                workspace_id=invite.workspace_id,
                email=invite.email,
                role=invite.role.value,
                token_hash=invite.token_hash,
                expires_at=invite.expires_at,
                created_at=invite.created_at,
                accepted_at=invite.accepted_at,
            )
        )
        await self._session.flush()
        self._append_events(invite)

    async def save(self, invite: Invite) -> None:
        row = await self._session.get(orm.InviteRow, invite.id)
        if row is None:
            await self.add(invite)
            return
        row.accepted_at = invite.accepted_at
        await self._session.flush()
        self._append_events(invite)


class SqlSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_token_hash(self, token_hash: str) -> Session | None:
        row = (
            await self._session.execute(
                sa.select(orm.SessionRow).where(orm.SessionRow.token_hash == token_hash)
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return Session(
            entity_id=row.id,
            user_id=row.user_id,
            token_hash=row.token_hash,
            family_id=row.family_id,
            expires_at=ensure_utc(row.expires_at) or row.expires_at,
            created_at=ensure_utc(row.created_at) or row.created_at,
            revoked_at=ensure_utc(row.revoked_at),
        )

    async def add(self, session: Session) -> None:
        self._session.add(
            orm.SessionRow(
                id=session.id,
                user_id=session.user_id,
                token_hash=session.token_hash,
                family_id=session.family_id,
                expires_at=session.expires_at,
                created_at=session.created_at,
                revoked_at=session.revoked_at,
            )
        )
        await self._session.flush()

    async def save(self, session: Session) -> None:
        row = await self._session.get(orm.SessionRow, session.id)
        if row is None:
            await self.add(session)
            return
        row.revoked_at = session.revoked_at
        await self._session.flush()

    async def revoke_family(self, family_id: uuid.UUID, now: datetime) -> None:
        await self._session.execute(
            sa.update(orm.SessionRow)
            .where(orm.SessionRow.family_id == family_id, orm.SessionRow.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID, now: datetime) -> None:
        await self._session.execute(
            sa.update(orm.SessionRow)
            .where(orm.SessionRow.user_id == user_id, orm.SessionRow.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self._session.flush()
