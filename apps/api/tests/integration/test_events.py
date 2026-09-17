"""RN-23/RN-25: toda mutacao gera evento auditavel no log append-only."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

import httpx
import sqlalchemy as sa
from tests.conftest import create_project, create_workspace, register_and_login

from cadencia.platform.orm import DomainEventRow
from cadencia.work.infrastructure.orm import WorkItemRow


async def _events(api_app: Any) -> list[DomainEventRow]:
    async with api_app.state.session_factory() as session:
        rows = (
            (await session.execute(sa.select(DomainEventRow).order_by(DomainEventRow.occurred_at)))
            .scalars()
            .all()
        )
        return list(rows)


async def test_full_flow_records_ordered_events_with_actor(
    client: httpx.AsyncClient, api_app: Any
) -> None:
    headers = await register_and_login(client)
    workspace = await create_workspace(client, headers)
    project = await create_project(client, headers, workspace["id"], key="EVT")

    item = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/items",
            json={"type": "STORY", "title": "Item auditado", "story_points": 5},
            headers=headers,
        )
    ).json()

    today = date.today()
    sprint = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/sprints",
            json={
                "name": "Sprint Audit",
                "goal": "Auditar eventos",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=13)).isoformat(),
            },
            headers=headers,
        )
    ).json()
    await client.put(
        f"/api/v1/workspaces/{workspace['id']}/items/{item['id']}/sprint",
        json={"sprint_id": sprint["id"]},
        headers=headers,
    )
    await client.post(
        f"/api/v1/workspaces/{workspace['id']}/sprints/{sprint['id']}/start", headers=headers
    )
    board = (
        await client.get(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/board", headers=headers
        )
    ).json()
    done_column = next(column for column in board["columns"] if column["category"] == "DONE")
    await client.post(
        f"/api/v1/workspaces/{workspace['id']}/items/{item['id']}/move",
        json={"column_id": done_column["id"], "index": 0},
        headers=headers,
    )

    events = await _events(api_app)
    types = [event.type for event in events]
    for expected in (
        "user.registered",
        "workspace.created",
        "project.created",
        "work_item.created",
        "sprint.created",
        "work_item.sprint_changed",
        "sprint.started",
        "work_item.completed",
        "work_item.moved",
    ):
        assert expected in types, f"evento ausente: {expected}"

    occurrences = [event.occurred_at for event in events]
    assert occurrences == sorted(occurrences)

    for event in events:
        if event.aggregate_type == "workitem":
            assert str(event.workspace_id) == workspace["id"]
            assert event.actor_id is not None
            assert event.source == "local"

    completed = next(event for event in events if event.type == "work_item.completed")
    assert completed.payload["story_points"] == 5

    sprint_events = [event for event in events if event.aggregate_type == "sprint"]
    assert [event.type for event in sprint_events] == ["sprint.created", "sprint.started"]


async def test_events_are_append_only_no_update_delete_apis(
    client: httpx.AsyncClient, api_app: Any
) -> None:
    """Nao existe superficie HTTP para mutar o event log (RN-25)."""
    headers = await register_and_login(client)
    await create_workspace(client, headers)
    events = await _events(api_app)
    assert len(events) >= 2

    event_id = events[0].id
    patch = await client.patch(f"/api/v1/events/{event_id}", json={}, headers=headers)
    delete = await client.delete(f"/api/v1/events/{event_id}", headers=headers)
    assert patch.status_code in {404, 405}
    assert delete.status_code in {404, 405}


async def test_workspace_scoping_matches_resources(client: httpx.AsyncClient, api_app: Any) -> None:
    headers = await register_and_login(client)
    workspace = await create_workspace(client, headers)
    project = await create_project(client, headers, workspace["id"], key="SCOPE")
    item = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/items",
            json={"type": "TASK", "title": "Escopado"},
            headers=headers,
        )
    ).json()

    async with api_app.state.session_factory() as session:
        row = await session.get(WorkItemRow, uuid.UUID(item["id"]))
    assert row is not None

    events = [event for event in await _events(api_app) if event.type == "work_item.created"]
    assert str(events[0].workspace_id) == workspace["id"]
    assert events[0].payload["title"] == "Escopado"
