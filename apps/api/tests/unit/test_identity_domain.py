"""Testes de dominio do contexto identity (RN-01..RN-04)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cadencia.identity.domain.entities import Invite, Session, User, Workspace, new_family_id
from cadencia.identity.domain.value_objects import (
    Role,
    normalize_email,
    role_at_least,
    slugify,
)
from cadencia.shared.errors import ConflictError, ForbiddenError, UnauthorizedError, ValidationError

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def test_role_ranking() -> None:
    assert role_at_least(Role.OWNER, Role.ADMIN)
    assert role_at_least(Role.ADMIN, Role.MEMBER)
    assert not role_at_least(Role.MEMBER, Role.ADMIN)
    assert not role_at_least(Role.VIEWER, Role.MEMBER)


def test_slugify_handles_accents_and_spaces() -> None:
    assert slugify("Acme Studio") == "acme-studio"
    assert slugify("Cadência Ágil") == "cadencia-agil"
    with pytest.raises(ValidationError):
        slugify("!!!")


def test_normalize_email() -> None:
    assert normalize_email("  User@Example.COM ") == "user@example.com"
    with pytest.raises(ValidationError):
        normalize_email("not-an-email")


def test_user_register_records_event() -> None:
    user = User.register(email="a@b.com", name="A", password_hash="hash", locale="pt-BR", now=NOW)
    events = user.pull_events()
    assert [event.event_type for event in events] == ["user.registered"]
    assert user.pull_events() == []


def test_workspace_create_validates_timezone() -> None:
    workspace = Workspace.create(
        organization_id=new_family_id(), name="Acme", timezone="America/Sao_Paulo", now=NOW
    )
    assert workspace.slug == "acme"
    assert workspace.working_days == (0, 1, 2, 3, 4)
    with pytest.raises(ValidationError):
        Workspace.create(
            organization_id=new_family_id(), name="Acme", timezone="Mars/Olympus", now=NOW
        )


def test_invite_lifecycle() -> None:
    invite = Invite.issue(
        workspace_id=new_family_id(),
        email="dev@example.com",
        role=Role.MEMBER,
        raw_token="token-123",
        now=NOW,
    )
    assert invite.is_open(NOW)

    with pytest.raises(ForbiddenError):
        invite.accept(user_email="outro@example.com", now=NOW)

    invite.accept(user_email="DEV@example.com", now=NOW)
    assert not invite.is_open(NOW)
    with pytest.raises(ConflictError):
        invite.accept(user_email="dev@example.com", now=NOW)


def test_expired_invite_cannot_be_accepted() -> None:
    invite = Invite.issue(
        workspace_id=new_family_id(),
        email="dev@example.com",
        role=Role.MEMBER,
        raw_token="token-123",
        now=NOW,
    )
    with pytest.raises(ConflictError):
        invite.accept(user_email="dev@example.com", now=NOW + timedelta(days=8))


def test_session_rotation_states() -> None:
    session = Session.issue(
        user_id=new_family_id(),
        token_hash="hash",
        family_id=new_family_id(),
        ttl_days=30,
        now=NOW,
    )
    session.ensure_active(NOW)
    session.revoke(NOW)
    assert session.is_revoked
    with pytest.raises(UnauthorizedError):
        session.ensure_active(NOW)


def test_expired_session_raises() -> None:
    session = Session.issue(
        user_id=new_family_id(),
        token_hash="hash",
        family_id=new_family_id(),
        ttl_days=1,
        now=NOW,
    )
    with pytest.raises(UnauthorizedError):
        session.ensure_active(NOW + timedelta(days=2))
