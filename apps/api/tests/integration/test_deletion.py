"""Exclusão de workspace (owner) e arquivamento de projeto/item."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import sqlalchemy as sa
from tests.conftest import create_project, create_workspace, register_and_login

from cadencia.platform.orm import DomainEventRow
from cadencia.work.infrastructure.orm import ProjectRow, WorkItemRow


async def test_owner_deletes_workspace_with_cascade(
    client: httpx.AsyncClient, api_app: Any
) -> None:
    headers = await register_and_login(client, email="owner@example.com")
    workspace = await create_workspace(client, headers)
    project = await create_project(client, headers, workspace["id"], key="DEL")
    await client.post(
        f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/items",
        json={"type": "TASK", "title": "Item que vai sumir"},
        headers=headers,
    )

    removed = await client.delete(f"/api/v1/workspaces/{workspace['id']}", headers=headers)
    assert removed.status_code == 204

    assert (await client.get("/api/v1/workspaces", headers=headers)).json() == []
    assert (
        await client.get(f"/api/v1/workspaces/{workspace['id']}", headers=headers)
    ).status_code == 404

    async with api_app.state.session_factory() as session:
        workspace_uuid = uuid.UUID(workspace["id"])
        projects = (
            await session.execute(
                sa.select(sa.func.count())
                .select_from(ProjectRow)
                .where(ProjectRow.workspace_id == workspace_uuid)
            )
        ).scalar_one()
        items = (
            await session.execute(
                sa.select(sa.func.count())
                .select_from(WorkItemRow)
                .where(WorkItemRow.project_id == uuid.UUID(project["id"]))
            )
        ).scalar_one()
        events = (
            await session.execute(
                sa.select(sa.func.count())
                .select_from(DomainEventRow)
                .where(DomainEventRow.workspace_id == workspace_uuid)
            )
        ).scalar_one()
    assert (projects, items, events) == (0, 0, 0)


async def test_non_owner_cannot_delete_workspace(client: httpx.AsyncClient) -> None:
    owner = await register_and_login(client, email="owner@example.com")
    workspace = await create_workspace(client, owner)
    invite = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/invites",
            json={"email": "admin@example.com", "role": "ADMIN"},
            headers=owner,
        )
    ).json()
    admin = await register_and_login(client, email="admin@example.com")
    await client.post(f"/api/v1/invites/{invite['token']}/accept", headers=admin)

    forbidden = await client.delete(f"/api/v1/workspaces/{workspace['id']}", headers=admin)
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "INSUFFICIENT_ROLE"


async def test_archive_project_hides_it_from_lists(client: httpx.AsyncClient) -> None:
    headers = await register_and_login(client)
    workspace = await create_workspace(client, headers)
    project = await create_project(client, headers, workspace["id"], key="ARC")

    archived = await client.delete(
        f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}",
        headers=headers,
    )
    assert archived.status_code == 204

    listed = await client.get(f"/api/v1/workspaces/{workspace['id']}/projects", headers=headers)
    assert listed.json() == []
    board = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/board",
        headers=headers,
    )
    assert board.status_code == 404
    assert board.json()["code"] == "PROJECT_NOT_FOUND"


async def test_archive_item_hides_it_from_board_and_backlog(
    client: httpx.AsyncClient,
) -> None:
    headers = await register_and_login(client)
    workspace = await create_workspace(client, headers)
    project = await create_project(client, headers, workspace["id"], key="ARI")
    item = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/items",
            json={"type": "STORY", "title": "Item arquivável", "story_points": 3},
            headers=headers,
        )
    ).json()

    archived = await client.delete(
        f"/api/v1/workspaces/{workspace['id']}/items/{item['id']}", headers=headers
    )
    assert archived.status_code == 204

    items = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/items",
        headers=headers,
    )
    assert items.json() == []

    again = await client.delete(
        f"/api/v1/workspaces/{workspace['id']}/items/{item['id']}", headers=headers
    )
    assert again.status_code == 409
    assert again.json()["code"] == "ITEM_ALREADY_ARCHIVED"
