"""Fluxo completo de trabalho: projeto, board, itens, sprint e regras de negocio."""

from __future__ import annotations

from datetime import date, timedelta

import httpx
from tests.conftest import create_project, create_workspace, register_and_login


async def _setup(client: httpx.AsyncClient) -> tuple[dict[str, str], str, dict]:
    headers = await register_and_login(client)
    workspace = await create_workspace(client, headers)
    project = await create_project(client, headers, workspace["id"])
    board = (
        await client.get(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/board",
            headers=headers,
        )
    ).json()
    return headers, workspace["id"], {"project": project, "board": board}


async def _create_item(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    workspace_id: str,
    project_id: str,
    **overrides: object,
) -> httpx.Response:
    payload = {
        "type": "STORY",
        "title": "Item",
        "story_points": 3,
        **overrides,
    }
    return await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/items",
        json=payload,
        headers=headers,
    )


async def test_default_board_has_three_categories(client: httpx.AsyncClient) -> None:
    _headers, _, ctx = await _setup(client)
    board = ctx["board"]
    assert [column["category"] for column in board["columns"]] == [
        "TODO",
        "IN_PROGRESS",
        "DONE",
    ]
    assert board["items"] == []


async def test_create_item_allocates_key_and_initial_column(client: httpx.AsyncClient) -> None:
    headers, workspace_id, ctx = await _setup(client)
    project = ctx["project"]
    first = await _create_item(client, headers, workspace_id, project["id"], title="Login")
    second = await _create_item(client, headers, workspace_id, project["id"], title="Dashboard")
    assert first.status_code == 201, first.text
    assert first.json()["key"] == "APP-1"
    assert second.json()["key"] == "APP-2"
    assert first.json()["status_category"] == "TODO"
    assert first.json()["version"] == 1


async def test_invalid_story_points_are_rejected(client: httpx.AsyncClient) -> None:
    headers, workspace_id, ctx = await _setup(client)
    response = await _create_item(
        client, headers, workspace_id, ctx["project"]["id"], story_points=4
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_STORY_POINTS"


async def test_move_item_to_done_and_reopen(client: httpx.AsyncClient) -> None:
    headers, workspace_id, ctx = await _setup(client)
    project, board = ctx["project"], ctx["board"]
    item = (await _create_item(client, headers, workspace_id, project["id"])).json()
    in_progress = next(c for c in board["columns"] if c["category"] == "IN_PROGRESS")
    done = next(c for c in board["columns"] if c["category"] == "DONE")

    moved = await client.post(
        f"/api/v1/workspaces/{workspace_id}/items/{item['id']}/move",
        json={"column_id": in_progress["id"], "index": 0, "expected_version": item["version"]},
        headers=headers,
    )
    assert moved.status_code == 200
    assert moved.json()["item"]["status_category"] == "IN_PROGRESS"

    completed = await client.post(
        f"/api/v1/workspaces/{workspace_id}/items/{item['id']}/move",
        json={"column_id": done["id"], "index": 0},
        headers=headers,
    )
    assert completed.status_code == 200
    assert completed.json()["item"]["done_at"] is not None

    reopened = await client.post(
        f"/api/v1/workspaces/{workspace_id}/items/{item['id']}/move",
        json={"column_id": board["columns"][0]["id"], "index": 0},
        headers=headers,
    )
    assert reopened.json()["item"]["done_at"] is None


async def test_stale_version_conflicts(client: httpx.AsyncClient) -> None:
    headers, workspace_id, ctx = await _setup(client)
    project, board = ctx["project"], ctx["board"]
    item = (await _create_item(client, headers, workspace_id, project["id"])).json()
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/items/{item['id']}/move",
        json={"column_id": board["columns"][1]["id"], "index": 0, "expected_version": 999},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "STALE_VERSION"


async def test_epic_cannot_have_parent(client: httpx.AsyncClient) -> None:
    headers, workspace_id, ctx = await _setup(client)
    project_id = ctx["project"]["id"]
    story = (await _create_item(client, headers, workspace_id, project_id, title="Story")).json()
    response = await _create_item(
        client,
        headers,
        workspace_id,
        project_id,
        type="EPIC",
        title="Epic filho",
        parent_id=story["id"],
        story_points=8,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "EPIC_WITH_PARENT"


async def test_sprint_lifecycle_with_carryover(client: httpx.AsyncClient) -> None:
    headers, workspace_id, ctx = await _setup(client)
    project, board = ctx["project"], ctx["board"]
    today = date.today()

    item_a = (await _create_item(client, headers, workspace_id, project["id"], title="A")).json()
    item_b = (await _create_item(client, headers, workspace_id, project["id"], title="B")).json()

    sprint_1 = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/sprints",
        json={
            "name": "Sprint 1",
            "goal": "Entregar A",
            "start_date": (today - timedelta(days=7)).isoformat(),
            "end_date": (today + timedelta(days=6)).isoformat(),
        },
        headers=headers,
    )
    assert sprint_1.status_code == 201, sprint_1.text
    sprint_1_id = sprint_1.json()["id"]

    # Iniciar sem goal está bloqueado (RN-16)
    bad = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/sprints",
        json={
            "name": "Sprint sem goal",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=13)).isoformat(),
        },
        headers=headers,
    )
    assert bad.status_code == 201
    empty_start = await client.post(
        f"/api/v1/workspaces/{workspace_id}/sprints/{bad.json()['id']}/start", headers=headers
    )
    assert empty_start.status_code == 422
    assert empty_start.json()["code"] == "SPRINT_GOAL_REQUIRED"

    # Sem itens atribuidos também bloqueia
    for item in (item_a, item_b):
        assign = await client.put(
            f"/api/v1/workspaces/{workspace_id}/items/{item['id']}/sprint",
            json={"sprint_id": sprint_1_id},
            headers=headers,
        )
        assert assign.status_code == 200

    started = await client.post(
        f"/api/v1/workspaces/{workspace_id}/sprints/{sprint_1_id}/start", headers=headers
    )
    assert started.status_code == 200
    assert started.json()["state"] == "ACTIVE"

    # Não pode haver duas sprints ativas (RN-15)
    second = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/sprints",
        json={
            "name": "Sprint 2",
            "goal": "Próxima",
            "start_date": (today + timedelta(days=7)).isoformat(),
            "end_date": (today + timedelta(days=20)).isoformat(),
        },
        headers=headers,
    )
    second_id = second.json()["id"]
    conflict = await client.post(
        f"/api/v1/workspaces/{workspace_id}/sprints/{second_id}/start", headers=headers
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "SPRINT_ALREADY_ACTIVE"

    # Concluir sprint 1 com carryover do item B para a sprint 2 (RN-17)
    done_column = next(c for c in board["columns"] if c["category"] == "DONE")
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/items/{item_a['id']}/move",
        json={"column_id": done_column["id"], "index": 0},
        headers=headers,
    )
    completed = await client.post(
        f"/api/v1/workspaces/{workspace_id}/sprints/{sprint_1_id}/complete",
        json={"target_sprint_id": second_id},
        headers=headers,
    )
    assert completed.status_code == 200
    assert completed.json()["state"] == "COMPLETED"
    assert completed.json()["done_items"] == 1

    items = (
        await client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/items", headers=headers
        )
    ).json()
    by_id = {item["id"]: item for item in items}
    assert by_id[item_b["id"]]["sprint_id"] == second_id
    assert by_id[item_a["id"]]["sprint_id"] == sprint_1_id


async def test_invalid_sprint_duration(client: httpx.AsyncClient) -> None:
    headers, workspace_id, ctx = await _setup(client)
    project_id = ctx["project"]["id"]
    today = date.today()
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/sprints",
        json={
            "name": "Curta",
            "goal": "x",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=3)).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SPRINT_DURATION"


async def test_duplicate_project_key_conflicts(client: httpx.AsyncClient) -> None:
    headers, workspace_id, _ = await _setup(client)
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        json={"name": "Outro", "key": "app"},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "PROJECT_KEY_EXISTS"
