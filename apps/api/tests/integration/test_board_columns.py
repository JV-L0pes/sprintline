"""Colunas configurÃ¡veis do board: criar, renomear, WIP, ordem e remover."""

from __future__ import annotations

import httpx
from tests.conftest import create_project, create_workspace, register_and_login


async def _setup(client: httpx.AsyncClient) -> tuple[dict[str, str], str, str, dict]:
    headers = await register_and_login(client)
    workspace = await create_workspace(client, headers)
    project = await create_project(client, headers, workspace["id"], key="COL")
    board = (
        await client.get(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/board",
            headers=headers,
        )
    ).json()
    return headers, workspace["id"], project["id"], board


async def test_create_column_appends_to_board(client: httpx.AsyncClient) -> None:
    headers, workspace_id, project_id, board = await _setup(client)
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/board/columns",
        json={"name": "In Review", "category": "IN_PROGRESS", "wip_limit": 4},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    names = [column["name"] for column in response.json()["columns"]]
    assert names == ["To Do", "In Progress", "Done", "In Review"]
    created = response.json()["columns"][-1]
    assert created["wip_limit"] == 4
    assert created["category"] == "IN_PROGRESS"
    assert len(board["columns"]) == 3


async def test_rename_and_wip_limit(client: httpx.AsyncClient) -> None:
    headers, workspace_id, project_id, board = await _setup(client)
    column_id = board["columns"][0]["id"]

    renamed = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/board/columns/{column_id}",
        json={"name": "Backlog", "wip_limit": 8},
        headers=headers,
    )
    assert renamed.status_code == 200
    updated = renamed.json()["columns"][0]
    assert updated["name"] == "Backlog"
    assert updated["wip_limit"] == 8

    cleared = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/board/columns/{column_id}",
        json={"clear_wip": True},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["columns"][0]["wip_limit"] is None


async def test_reorder_columns(client: httpx.AsyncClient) -> None:
    headers, workspace_id, project_id, board = await _setup(client)
    ids = [column["id"] for column in board["columns"]]
    reordered = await client.put(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/board/columns/order",
        json={"column_ids": [ids[2], ids[0], ids[1]]},
        headers=headers,
    )
    assert reordered.status_code == 200
    assert [column["id"] for column in reordered.json()["columns"]] == [ids[2], ids[0], ids[1]]

    invalid = await client.put(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/board/columns/order",
        json={"column_ids": [ids[0], ids[1]]},
        headers=headers,
    )
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "INVALID_COLUMN_ORDER"


async def test_delete_column_rules(client: httpx.AsyncClient) -> None:
    headers, workspace_id, project_id, board = await _setup(client)
    todo_id = board["columns"][0]["id"]

    # NÃ£o pode remover a Ãºltima coluna de uma categoria (RN-06)
    last_of_category = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/board/columns/{todo_id}",
        headers=headers,
    )
    assert last_of_category.status_code == 422
    assert last_of_category.json()["code"] == "BOARD_LAST_CATEGORY_COLUMN"

    # Cria uma segunda coluna TODO e remove a original
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/board/columns",
        json={"name": "Icebox", "category": "TODO"},
        headers=headers,
    )
    removed = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/board/columns/{todo_id}",
        headers=headers,
    )
    assert removed.status_code == 200
    assert [column["name"] for column in removed.json()["columns"]] == [
        "In Progress",
        "Done",
        "Icebox",
    ]


async def test_delete_non_empty_column_is_blocked(client: httpx.AsyncClient) -> None:
    headers, workspace_id, project_id, board = await _setup(client)
    todo_id = board["columns"][0]["id"]
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/board/columns",
        json={"name": "Icebox", "category": "TODO"},
        headers=headers,
    )
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/items",
        json={"type": "TASK", "title": "Item no TODO"},
        headers=headers,
    )
    blocked = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/board/columns/{todo_id}",
        headers=headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "COLUMN_NOT_EMPTY"


async def test_change_column_category_with_coverage_guard(
    client: httpx.AsyncClient,
) -> None:
    headers, workspace_id, project_id, board = await _setup(client)
    base = f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/board/columns"
    created = (
        await client.post(
            base,
            json={"name": "Refinamento", "category": "TODO"},
            headers=headers,
        )
    ).json()
    first_todo = board["columns"][0]
    extra_todo = created["columns"][-1]

    moved = await client.patch(
        f"{base}/{first_todo['id']}",
        json={"category": "IN_PROGRESS"},
        headers=headers,
    )
    assert moved.status_code == 200
    categories = {column["id"]: column["category"] for column in moved.json()["columns"]}
    assert categories[first_todo["id"]] == "IN_PROGRESS"

    # Refinamento virou a unica coluna TODO: mudar de categoria deve ser bloqueado
    blocked = await client.patch(
        f"{base}/{extra_todo['id']}",
        json={"category": "IN_PROGRESS"},
        headers=headers,
    )
    assert blocked.status_code == 422
    assert blocked.json()["code"] == "BOARD_LAST_CATEGORY_COLUMN"

    # renomear nao mexe na categoria
    in_progress_id = board["columns"][1]["id"]
    renamed = await client.patch(
        f"{base}/{in_progress_id}",
        json={"name": "Em andamento"},
        headers=headers,
    )
    assert renamed.status_code == 200
    row = next(column for column in renamed.json()["columns"] if column["id"] == in_progress_id)
    assert (row["name"], row["category"]) == ("Em andamento", "IN_PROGRESS")
