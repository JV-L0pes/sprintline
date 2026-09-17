"""Fluxo e2e completo: do cadastro ao burndown com dados reais."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import time_machine
from tests.conftest import DEMO

FIXED_NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


async def test_full_journey(client: httpx.AsyncClient) -> None:
    with time_machine.travel(FIXED_NOW, tick=False):
        register = await client.post("/api/v1/auth/register", json=DEMO)
        assert register.status_code == 201

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": DEMO["email"], "password": DEMO["password"]},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        workspace = (
            await client.post("/api/v1/workspaces", json={"name": "Acme"}, headers=headers)
        ).json()
        workspace_id = workspace["id"]

        project = (
            await client.post(
                f"/api/v1/workspaces/{workspace_id}/projects",
                json={"name": "App Mobile", "key": "APP"},
                headers=headers,
            )
        ).json()

        item = (
            await client.post(
                f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/items",
                json={"type": "STORY", "title": "Login", "story_points": 5},
                headers=headers,
            )
        ).json()
        assert item["key"] == "APP-1"

        today = FIXED_NOW.date()
        sprint = (
            await client.post(
                f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/sprints",
                json={
                    "name": "Sprint 1",
                    "goal": "Login funcionando",
                    "start_date": (today - timedelta(days=3)).isoformat(),
                    "end_date": (today + timedelta(days=10)).isoformat(),
                },
                headers=headers,
            )
        ).json()

        await client.put(
            f"/api/v1/workspaces/{workspace_id}/items/{item['id']}/sprint",
            json={"sprint_id": sprint["id"]},
            headers=headers,
        )
        started = await client.post(
            f"/api/v1/workspaces/{workspace_id}/sprints/{sprint['id']}/start",
            headers=headers,
        )
        assert started.json()["state"] == "ACTIVE"
        assert started.json()["total_points"] == 5

        board = (
            await client.get(
                f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/board",
                headers=headers,
            )
        ).json()
        done_column = next(c for c in board["columns"] if c["category"] == "DONE")
        await client.post(
            f"/api/v1/workspaces/{workspace_id}/items/{item['id']}/move",
            json={"column_id": done_column["id"], "index": 0},
            headers=headers,
        )

        burndown = (
            await client.get(
                f"/api/v1/workspaces/{workspace_id}/sprints/{sprint['id']}/burndown",
                headers=headers,
            )
        ).json()
        # Item entrou no sprint apos o inicio (start = hoje-3): escopo inicial 0,
        # degrau de +5 registrado como mudanca de escopo (RM-02).
        assert burndown["totals"]["completed"] == 5
        assert burndown["totals"]["initial_scope"] == 0
        assert burndown["totals"]["final_scope"] == 5
        assert sum(change["delta"] for change in burndown["scope_changes"]) == 5
        assert burndown["days"][-1]["remaining"] == 0
        assert burndown["days"][-1]["completed"] == 5

        completed = await client.post(
            f"/api/v1/workspaces/{workspace_id}/sprints/{sprint['id']}/complete",
            json={},
            headers=headers,
        )
        assert completed.json()["state"] == "COMPLETED"

        velocity = (
            await client.get(
                f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/velocity",
                headers=headers,
            )
        ).json()
        assert velocity["average"] == 5
