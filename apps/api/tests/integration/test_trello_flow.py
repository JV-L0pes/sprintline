"""Fluxo Trello com gateway fake: connect, boards, import idempotente e webhook."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from tests.conftest import create_workspace, register_and_login

from cadencia.integrations.domain.ports import (
    TrelloBoard,
    TrelloCard,
    TrelloList,
    TrelloMember,
)
from cadencia.platform.security import webhook_token


class FakeTrelloGateway:
    def __init__(self) -> None:
        self.boards = [
            TrelloBoard(id="b1", name="Produto", url="https://trello.com/b/b1", closed=False)
        ]
        self.lists = [
            TrelloList(id="l-todo", name="Backlog", pos=1.0),
            TrelloList(id="l-doing", name="Doing", pos=2.0),
            TrelloList(id="l-done", name="Done", pos=3.0),
        ]
        self.cards = [
            TrelloCard(
                id="c1",
                id_list="l-done",
                name="Login com SSO (5)",
                desc="",
                url="https://trello.com/c/c1",
                closed=False,
                labels=("Story",),
                due=None,
            ),
            TrelloCard(
                id="c2",
                id_list="l-doing",
                name="Corrigir crash",
                desc="",
                url="https://trello.com/c/c2",
                closed=False,
                labels=("Bug",),
                due=None,
            ),
            TrelloCard(
                id="c3",
                id_list="l-todo",
                name="Card arquivado",
                desc="",
                url="https://trello.com/c/c3",
                closed=True,
                labels=(),
                due=None,
            ),
        ]
        self.webhooks: list[tuple[str, str]] = []

    def build_authorize_url(self, return_url: str) -> str:
        return f"https://trello.com/1/authorize?key=test&return_url={return_url}"

    async def member_me(self, token: str) -> TrelloMember:
        if not token.startswith("trello-"):
            raise ValueError("token invalido")
        return TrelloMember(id="m1", username="dev", full_name="Dev Runner")

    async def member_boards(self, token: str) -> list[TrelloBoard]:
        return list(self.boards)

    async def get_board(self, token: str, board_id: str) -> TrelloBoard | None:
        return next((board for board in self.boards if board.id == board_id), None)

    async def board_lists(self, token: str, board_id: str) -> list[TrelloList]:
        return list(self.lists)

    async def board_cards(self, token: str, board_id: str) -> list[TrelloCard]:
        return sorted(self.cards, key=lambda card: card.id)

    async def get_card(self, token: str, card_id: str) -> TrelloCard | None:
        return next((card for card in self.cards if card.id == card_id), None)

    async def register_webhook(
        self, token: str, board_id: str, callback_url: str, description: str
    ) -> str | None:
        self.webhooks.append((board_id, callback_url))
        return "wh1"


@pytest.fixture
async def trello_gateway(api_app: Any) -> FakeTrelloGateway:
    gateway = FakeTrelloGateway()
    api_app.state.trello_gateway = gateway
    api_app.state.settings.trello_api_key = "test-key"
    yield gateway
    del api_app.state.trello_gateway
    api_app.state.settings.trello_api_key = ""


async def _connect(client: httpx.AsyncClient, headers: dict[str, str]) -> str:
    workspace = await create_workspace(client, headers, name="Trello WS")
    response = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/integrations/trello/connect",
        json={"token": "trello-token-123456"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return workspace["id"]


async def test_connect_lists_boards_and_registers_webhook(
    client: httpx.AsyncClient, trello_gateway: FakeTrelloGateway
) -> None:
    headers = await register_and_login(client)
    workspace_id = await _connect(client, headers)

    integrations = (
        await client.get(f"/api/v1/workspaces/{workspace_id}/integrations", headers=headers)
    ).json()
    assert len(integrations) == 1
    connection_id = integrations[0]["id"]
    assert integrations[0]["provider"] == "TRELLO"
    assert integrations[0]["site_url"] == "https://trello.com/dev"

    boards = await client.get(
        f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/trello/boards",
        headers=headers,
    )
    assert boards.status_code == 200, boards.text
    assert [board["name"] for board in boards.json()] == ["Produto"]

    authorize = await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/trello/authorize", headers=headers
    )
    assert authorize.status_code == 200
    assert "return_url=" in authorize.json()["authorize_url"]


async def test_import_maps_lists_labels_and_points(
    client: httpx.AsyncClient, trello_gateway: FakeTrelloGateway
) -> None:
    headers = await register_and_login(client)
    workspace_id = await _connect(client, headers)
    connection_id = (
        await client.get(f"/api/v1/workspaces/{workspace_id}/integrations", headers=headers)
    ).json()[0]["id"]

    started = await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/trello/import",
        json={"board_id": "b1"},
        headers=headers,
    )
    assert started.status_code == 201, started.text
    job_id = started.json()["id"]

    ran = await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/jobs/{job_id}/run",
        headers=headers,
    )
    assert ran.status_code == 200, ran.text
    assert ran.json()["state"] == "DONE"
    assert ran.json()["imported_count"] == 2  # card arquivado e ignorado

    project = next(
        item
        for item in (
            await client.get(f"/api/v1/workspaces/{workspace_id}/projects", headers=headers)
        ).json()
        if item["key"] == "PRODUTO"
    )
    items = (
        await client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/items", headers=headers
        )
    ).json()
    assert len(items) == 2
    by_title = {item["title"]: item for item in items}
    login = by_title["Login com SSO (5)"]
    assert login["story_points"] == 5
    assert login["type"] == "STORY"
    assert login["status_category"] == "DONE"  # lista "Done"
    crash = by_title["Corrigir crash"]
    assert crash["type"] == "BUG"
    assert crash["status_category"] == "IN_PROGRESS"  # lista "Doing"
    assert "trello.com/c/c2" in crash["description"]

    # Webhook do board registrado ao concluir a importacao (best-effort)
    assert len(trello_gateway.webhooks) == 1
    assert trello_gateway.webhooks[0][0] == "b1"

    # Reexecucao bloqueada e sem duplicacao (RN-20)
    again = await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/jobs/{job_id}/run",
        headers=headers,
    )
    assert again.status_code == 409
    assert again.json()["code"] == "JOB_ALREADY_DONE"


async def test_webhook_dedupes_and_moves_card(
    client: httpx.AsyncClient, trello_gateway: FakeTrelloGateway, api_app: Any
) -> None:
    headers = await register_and_login(client)
    workspace_id = await _connect(client, headers)
    connection_id = (
        await client.get(f"/api/v1/workspaces/{workspace_id}/integrations", headers=headers)
    ).json()[0]["id"]
    job = (
        await client.post(
            f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/trello/import",
            json={"board_id": "b1"},
            headers=headers,
        )
    ).json()
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/{connection_id}/jobs/{job['id']}/run",
        headers=headers,
    )

    # O card se moveu para "Done" no Trello
    for index, card in enumerate(trello_gateway.cards):
        if card.id == "c2":
            trello_gateway.cards[index] = TrelloCard(
                id=card.id,
                id_list="l-done",
                name=card.name,
                desc=card.desc,
                url=card.url,
                closed=False,
                labels=card.labels,
                due=None,
            )

    token = webhook_token(connection_id, api_app.state.settings)
    payload = {
        "action": {
            "id": "action-1",
            "type": "updateCard",
            "data": {"card": {"id": "c2"}},
        }
    }
    first = await client.post(
        f"/api/v1/integrations/trello/webhook/{connection_id}?token={token}", json=payload
    )
    assert first.status_code == 200
    assert first.json()["status"] == "accepted"

    # Mesmo action de novo -> duplicate
    second = await client.post(
        f"/api/v1/integrations/trello/webhook/{connection_id}?token={token}", json=payload
    )
    assert second.json()["status"] == "duplicate"

    project = next(
        item
        for item in (
            await client.get(f"/api/v1/workspaces/{workspace_id}/projects", headers=headers)
        ).json()
        if item["key"] == "PRODUTO"
    )
    items = (
        await client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}/items", headers=headers
        )
    ).json()
    crash = next(item for item in items if item["title"] == "Corrigir crash")
    assert crash["status_category"] == "DONE"
    assert crash["done_at"] is not None

    # Token errado na URL publica -> 404
    bad = await client.post(
        f"/api/v1/integrations/trello/webhook/{connection_id}?token=errado", json=payload
    )
    assert bad.status_code == 404


async def test_trello_requires_admin_role(
    client: httpx.AsyncClient, trello_gateway: FakeTrelloGateway
) -> None:
    owner = await register_and_login(client, email="owner@example.com")
    workspace = await create_workspace(client, owner)
    invite = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/invites",
            json={"email": "member@example.com", "role": "MEMBER"},
            headers=owner,
        )
    ).json()
    member = await register_and_login(client, email="member@example.com")
    await client.post(f"/api/v1/invites/{invite['token']}/accept", headers=member)

    forbidden = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/integrations/trello/connect",
        json={"token": "trello-token-123456"},
        headers=member,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "INSUFFICIENT_ROLE"
