"""RN-02: isolamento entre workspaces e fluxo de convite."""

from __future__ import annotations

import httpx
from tests.conftest import create_project, create_workspace, register_and_login


async def test_non_member_gets_404_not_403(client: httpx.AsyncClient) -> None:
    owner = await register_and_login(client, email="owner@example.com")
    workspace = await create_workspace(client, owner)
    project = await create_project(client, owner, workspace["id"])

    intruder = await register_and_login(client, email="intruder@example.com")

    assert (await client.get("/api/v1/workspaces", headers=intruder)).json() == []

    for path in (
        f"/api/v1/workspaces/{workspace['id']}",
        f"/api/v1/workspaces/{workspace['id']}/members",
        f"/api/v1/workspaces/{workspace['id']}/projects",
        f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/board",
        f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/items",
    ):
        response = await client.get(path, headers=intruder)
        assert response.status_code == 404, path
        assert response.json()["code"] == "WORKSPACE_NOT_FOUND"


async def test_invite_flow_grants_access(client: httpx.AsyncClient) -> None:
    owner = await register_and_login(client, email="owner@example.com")
    workspace = await create_workspace(client, owner)

    invite = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/invites",
        json={"email": "dev@example.com", "role": "MEMBER"},
        headers=owner,
    )
    assert invite.status_code == 201, invite.text
    token = invite.json()["token"]

    developer = await register_and_login(client, email="dev@example.com")
    accepted = await client.post(f"/api/v1/invites/{token}/accept", headers=developer)
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["workspace"]["id"] == workspace["id"]

    listing = await client.get("/api/v1/workspaces", headers=developer)
    assert [item["id"] for item in listing.json()] == [workspace["id"]]

    members = await client.get(f"/api/v1/workspaces/{workspace['id']}/members", headers=developer)
    assert members.status_code == 200
    assert len(members.json()) == 2

    # Convite reutilizado falha (RN-03)
    again = await client.post(f"/api/v1/invites/{token}/accept", headers=developer)
    assert again.status_code == 409


async def test_invite_requires_admin_role(client: httpx.AsyncClient) -> None:
    owner = await register_and_login(client, email="owner@example.com")
    workspace = await create_workspace(client, owner)
    invite = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/invites",
        json={"email": "member@example.com", "role": "MEMBER"},
        headers=owner,
    )
    member = await register_and_login(client, email="member@example.com")
    await client.post(f"/api/v1/invites/{invite.json()['token']}/accept", headers=member)

    forbidden = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/invites",
        json={"email": "outro@example.com", "role": "MEMBER"},
        headers=member,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "INSUFFICIENT_ROLE"


async def test_admin_cannot_escalate_to_owner(client: httpx.AsyncClient) -> None:
    owner = await register_and_login(client, email="owner@example.com")
    workspace = await create_workspace(client, owner)
    invite = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/invites",
        json={"email": "admin@example.com", "role": "ADMIN"},
        headers=owner,
    )
    admin = await register_and_login(client, email="admin@example.com")
    await client.post(f"/api/v1/invites/{invite.json()['token']}/accept", headers=admin)

    escalation = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/invites",
        json={"email": "novo@example.com", "role": "OWNER"},
        headers=admin,
    )
    assert escalation.status_code == 403
    assert escalation.json()["code"] == "ROLE_ESCALATION"
