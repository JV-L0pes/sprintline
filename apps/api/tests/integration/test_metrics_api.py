"""Metricas de ponta a ponta: os numeros do burndown refletem o event log."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import time_machine
from tests.conftest import create_project, create_workspace, register_and_login

FIXED_NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)  # quarta-feira


async def _scenario(client: httpx.AsyncClient) -> dict:
    headers = await register_and_login(client)
    workspace = await create_workspace(client, headers)
    project = await create_project(client, headers, workspace["id"], key="MET")
    workspace_id = workspace["id"]
    today = FIXED_NOW.date()

    async def create_item(title: str, points: int) -> dict:
        response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/items",
            json={"type": "STORY", "title": title, "story_points": points},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        return response.json()

    item_a = await create_item("Login", 5)
    item_b = await create_item("Dashboard", 8)

    sprint = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/sprints",
        json={
            "name": "Sprint 1",
            "goal": "Entregar login",
            "start_date": (today - timedelta(days=7)).isoformat(),
            "end_date": (today + timedelta(days=6)).isoformat(),
        },
        headers=headers,
    )
    sprint_id = sprint.json()["id"]
    for item in (item_a, item_b):
        await client.put(
            f"/api/v1/workspaces/{workspace_id}/items/{item['id']}/sprint",
            json={"sprint_id": sprint_id},
            headers=headers,
        )
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/sprints/{sprint_id}/start", headers=headers
    )

    board = (
        await client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/board",
            headers=headers,
        )
    ).json()
    in_progress_column = next(
        column for column in board["columns"] if column["category"] == "IN_PROGRESS"
    )
    done_column = next(column for column in board["columns"] if column["category"] == "DONE")
    started_item = await client.post(
        f"/api/v1/workspaces/{workspace_id}/items/{item_a['id']}/move",
        json={"column_id": in_progress_column["id"], "index": 0},
        headers=headers,
    )
    assert started_item.status_code == 200
    moved = await client.post(
        f"/api/v1/workspaces/{workspace_id}/items/{item_a['id']}/move",
        json={"column_id": done_column["id"], "index": 0},
        headers=headers,
    )
    assert moved.status_code == 200

    return {
        "headers": headers,
        "workspace_id": workspace_id,
        "project_id": project["id"],
        "sprint_id": sprint_id,
    }


async def test_burndown_endpoint_reflects_real_events(client: httpx.AsyncClient) -> None:
    with time_machine.travel(FIXED_NOW, tick=False):
        ctx = await _scenario(client)
        response = await client.get(
            f"/api/v1/workspaces/{ctx['workspace_id']}/sprints/{ctx['sprint_id']}/burndown",
            headers=ctx["headers"],
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["unit"] == "points"
        assert len(body["days"]) == 10
        # Itens entraram no sprint no meio do periodo: degrau de escopo visivel (RM-02)
        assert body["days"][0]["remaining"] == 0
        assert body["days"][0]["ideal"] == 0
        assert body["days"][-1]["ideal"] == 0
        assert body["totals"]["initial_scope"] == 0
        assert body["totals"]["final_scope"] == 13
        assert body["totals"]["completed"] == 5
        assert body["days"][-1]["remaining"] == 8
        changes = body["scope_changes"]
        assert len(changes) == 2
        assert {change["kind"] for change in changes} == {"added"}
        assert sum(change["delta"] for change in changes) == 13
        assert {change["date"] for change in changes} == {"2026-09-16"}
        # Concluido nunca retroage apos o dia do evento
        assert body["days"][0]["completed"] == 0


async def test_velocity_cfd_and_flow_times(client: httpx.AsyncClient) -> None:
    with time_machine.travel(FIXED_NOW, tick=False):
        ctx = await _scenario(client)
        velocity = await client.get(
            f"/api/v1/workspaces/{ctx['workspace_id']}/projects/{ctx['project_id']}/velocity",
            headers=ctx["headers"],
        )
        assert velocity.status_code == 200
        body = velocity.json()
        assert body["sprints"][0]["committed"] == 0
        assert body["sprints"][0]["completed"] == 5
        assert body["sprints"][0]["added"] == 13
        assert body["average"] == 5

        cfd = await client.get(
            f"/api/v1/workspaces/{ctx['workspace_id']}/sprints/{ctx['sprint_id']}/cfd",
            headers=ctx["headers"],
        )
        assert cfd.status_code == 200
        days = cfd.json()["days"]
        assert len(days) == 10
        assert days[-1]["counts"]["DONE"] == 1
        assert days[-1]["counts"]["TODO"] == 1

        flow = await client.get(
            f"/api/v1/workspaces/{ctx['workspace_id']}/projects/{ctx['project_id']}/flow-times",
            headers=ctx["headers"],
        )
        assert flow.status_code == 200
        assert flow.json()["count"] == 1
        assert flow.json()["lead_p50"] is not None
        assert flow.json()["cycle_p50"] is not None


async def test_metrics_require_workspace_membership(client: httpx.AsyncClient) -> None:
    with time_machine.travel(FIXED_NOW, tick=False):
        ctx = await _scenario(client)
        outsider = await register_and_login(client, email="outsider@example.com")
        response = await client.get(
            f"/api/v1/workspaces/{ctx['workspace_id']}/sprints/{ctx['sprint_id']}/burndown",
            headers=outsider,
        )
        assert response.status_code == 404
