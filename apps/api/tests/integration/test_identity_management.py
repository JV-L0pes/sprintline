"""GestÃ£o de identidade: rate limit, registro por convite, membros e senhas."""

from __future__ import annotations

from typing import Any

import httpx
from tests.conftest import DEMO, create_workspace, register_and_login


async def test_rate_limit_login_returns_429_with_retry_after(
    client: httpx.AsyncClient, api_app: Any
) -> None:
    settings = api_app.state.settings
    original = settings.login_max_attempts
    settings.login_max_attempts = 2
    try:
        await client.post("/api/v1/auth/register", json=DEMO)
        for _ in range(2):
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": DEMO["email"], "password": "senha-errada-1"},
            )
            assert response.status_code == 401
        blocked = await client.post(
            "/api/v1/auth/login",
            json={"email": DEMO["email"], "password": DEMO["password"]},
        )
        assert blocked.status_code == 429
        assert blocked.json()["code"] == "RATE_LIMITED"
        assert int(blocked.headers["retry-after"]) >= 1
    finally:
        settings.login_max_attempts = original


async def test_registration_requires_invite_when_configured(
    client: httpx.AsyncClient, api_app: Any
) -> None:
    # O owner da casa nasce antes de fecharmos o registro
    owner = await register_and_login(client, email="dono@example.com")
    workspace = await create_workspace(client, owner)
    invite = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/invites",
            json={"email": "convidado@example.com", "role": "MEMBER"},
            headers=owner,
        )
    ).json()

    settings = api_app.state.settings
    original = settings.registration_mode
    settings.registration_mode = "invite_only"
    try:
        refused = await client.post(
            "/api/v1/auth/register",
            json={**DEMO, "email": "sem-convite@example.com"},
        )
        assert refused.status_code == 403
        assert refused.json()["code"] == "REGISTRATION_INVITE_REQUIRED"

        wrong_email = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "outro@example.com",
                "name": "Outro",
                "password": "senha-super-secreta",
                "invite_token": invite["token"],
            },
        )
        assert wrong_email.status_code == 403
        assert wrong_email.json()["code"] == "INVITE_EMAIL_MISMATCH"

        registered = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "convidado@example.com",
                "name": "Convidado",
                "password": "senha-super-secreta",
                "invite_token": invite["token"],
            },
        )
        assert registered.status_code == 201, registered.text
    finally:
        settings.registration_mode = original


async def _workspace_with_member(client: httpx.AsyncClient) -> tuple[dict, str, dict, str]:
    owner = await register_and_login(client, email="owner@example.com")
    workspace = await create_workspace(client, owner)
    invite = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/invites",
            json={"email": "dev@example.com", "role": "MEMBER"},
            headers=owner,
        )
    ).json()
    member = await register_and_login(client, email="dev@example.com")
    await client.post(f"/api/v1/invites/{invite['token']}/accept", headers=member)
    members = (
        await client.get(f"/api/v1/workspaces/{workspace['id']}/members", headers=owner)
    ).json()
    member_id = next(entry["user_id"] for entry in members if entry["email"] == "dev@example.com")
    return owner, workspace["id"], member, member_id


async def test_member_role_change_rules(client: httpx.AsyncClient) -> None:
    owner, workspace_id, _member, member_id = await _workspace_with_member(client)
    owner_id = (await client.get("/api/v1/auth/me", headers=owner)).json()["id"]

    promoted = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{member_id}",
        json={"role": "ADMIN"},
        headers=owner,
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "ADMIN"

    # Admin nÃ£o gerencia owner nem promove a owner (escalation)
    as_admin = await register_and_login(client, email="admin2@example.com")
    invite = (
        await client.post(
            f"/api/v1/workspaces/{workspace_id}/invites",
            json={"email": "admin2@example.com", "role": "ADMIN"},
            headers=owner,
        )
    ).json()
    await client.post(f"/api/v1/invites/{invite['token']}/accept", headers=as_admin)
    cannot_manage_owner = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{owner_id}",
        json={"role": "MEMBER"},
        headers=as_admin,
    )
    assert cannot_manage_owner.status_code == 403
    assert cannot_manage_owner.json()["code"] == "CANNOT_MANAGE_MEMBER"

    # Owner nÃ£o altera o prÃ³prio papel (evita lockout)
    self_change = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{owner_id}",
        json={"role": "MEMBER"},
        headers=owner,
    )
    assert self_change.status_code == 409
    assert self_change.json()["code"] == "CANNOT_MANAGE_SELF"

    # Viewer (sem admin) recebe 403 do gate de papel
    viewer = await register_and_login(client, email="viewer@example.com")
    viewer_invite = (
        await client.post(
            f"/api/v1/workspaces/{workspace_id}/invites",
            json={"email": "viewer@example.com", "role": "VIEWER"},
            headers=owner,
        )
    ).json()
    await client.post(f"/api/v1/invites/{viewer_invite['token']}/accept", headers=viewer)
    forbidden = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{member_id}",
        json={"role": "VIEWER"},
        headers=viewer,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "INSUFFICIENT_ROLE"


async def test_remove_member_and_last_owner_protection(client: httpx.AsyncClient) -> None:
    owner, workspace_id, member, member_id = await _workspace_with_member(client)
    owner_id = (await client.get("/api/v1/auth/me", headers=owner)).json()["id"]

    removed = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{member_id}", headers=owner
    )
    assert removed.status_code == 204
    assert (
        await client.get(f"/api/v1/workspaces/{workspace_id}", headers=member)
    ).status_code == 404

    last_owner = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{owner_id}", headers=owner
    )
    assert last_owner.status_code == 409
    assert last_owner.json()["code"] == "CANNOT_MANAGE_SELF"


async def test_admin_resets_member_password(client: httpx.AsyncClient) -> None:
    owner, workspace_id, _member, member_id = await _workspace_with_member(client)

    reset = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members/{member_id}/password",
        json={"new_password": "nova-senha-secreta-1"},
        headers=owner,
    )
    assert reset.status_code == 204

    # SessÃµes do membro revogadas (o cookie atual do client pertence a ele)
    after_reset = await client.post("/api/v1/auth/refresh")
    assert after_reset.status_code == 401
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "dev@example.com", "password": "super-secret-1"},
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "dev@example.com", "password": "nova-senha-secreta-1"},
    )
    assert new_login.status_code == 200


async def test_change_own_password(client: httpx.AsyncClient) -> None:
    headers = await register_and_login(client, email="change@example.com")
    wrong = await client.post(
        "/api/v1/auth/password",
        json={"current_password": "errada-errada", "new_password": "outra-senha-boa-1"},
        headers=headers,
    )
    assert wrong.status_code == 401
    assert wrong.json()["code"] == "INVALID_CURRENT_PASSWORD"

    changed = await client.post(
        "/api/v1/auth/password",
        json={"current_password": DEMO["password"], "new_password": "outra-senha-boa-1"},
        headers=headers,
    )
    assert changed.status_code == 204

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "change@example.com", "password": DEMO["password"]},
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "change@example.com", "password": "outra-senha-boa-1"},
    )
    assert new_login.status_code == 200


async def test_meta_exposes_registration_mode(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["registration_mode"] == "open"
    assert body["app_name"]


async def test_update_workspace_renames_and_keeps_slug(client: httpx.AsyncClient) -> None:
    headers = await register_and_login(client, email="renomeador@example.com")
    workspace = await create_workspace(client, headers)
    original_slug = workspace["slug"]

    updated = await client.patch(
        f"/api/v1/workspaces/{workspace['id']}",
        json={"name": "Time Renomeado", "timezone": "America/Bahia"},
        headers=headers,
    )
    assert updated.status_code == 200
    body = updated.json()
    assert (body["name"], body["timezone"], body["slug"]) == (
        "Time Renomeado",
        "America/Bahia",
        original_slug,
    )


async def test_update_workspace_rejects_invalid_timezone_and_member(
    client: httpx.AsyncClient,
) -> None:
    owner = await register_and_login(client, email="dona@example.com")
    workspace = await create_workspace(client, owner)
    invite = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/invites",
            json={"email": "membro@example.com", "role": "MEMBER"},
            headers=owner,
        )
    ).json()
    member = await register_and_login(client, email="membro@example.com")
    await client.post(f"/api/v1/invites/{invite['token']}/accept", headers=member)

    forbidden = await client.patch(
        f"/api/v1/workspaces/{workspace['id']}",
        json={"name": "Nao Pode"},
        headers=member,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "INSUFFICIENT_ROLE"

    invalid = await client.patch(
        f"/api/v1/workspaces/{workspace['id']}",
        json={"timezone": "Marte/Olympus"},
        headers=owner,
    )
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "INVALID_TIMEZONE"
