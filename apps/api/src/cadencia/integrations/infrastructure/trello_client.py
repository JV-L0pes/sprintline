"""Cliente HTTP do Trello (API key do app + token do usuario)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from cadencia.integrations.domain.ports import (
    TrelloBoard,
    TrelloCard,
    TrelloList,
    TrelloMember,
)
from cadencia.platform.config import Settings

API_BASE = "https://api.trello.com/1"
AUTHORIZE_BASE = "https://trello.com/1/authorize"
_CARD_FIELDS = "name,desc,url,closed,idList,due,labels"
_CARD_LIMIT = 1000


class TrelloApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"Trello API {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class HttpxTrelloGateway:
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._http = http

    # ---------------------------------------------------------- authorize ---
    def build_authorize_url(self, return_url: str) -> str:
        params = {
            "expiration": "never",
            "name": self._settings.trello_app_name,
            "scope": "read,write",
            "response_type": "token",
            "key": self._settings.trello_api_key,
            "return_url": return_url,
        }
        return f"{AUTHORIZE_BASE}?{urlencode(params)}"

    # ---------------------------------------------------------------- API ---
    async def member_me(self, token: str) -> TrelloMember:
        data = await self._get_json(
            "/members/me", token=token, params={"fields": "id,username,fullname"}
        )
        return TrelloMember(
            id=str(data["id"]),
            username=str(data.get("username", "")),
            full_name=str(data.get("fullname", "")),
        )

    async def member_boards(self, token: str) -> list[TrelloBoard]:
        data = await self._get_json(
            "/members/me/boards",
            token=token,
            params={"filter": "open", "fields": "name,url,closed"},
        )
        return [self._board(raw) for raw in data]

    async def get_board(self, token: str, board_id: str) -> TrelloBoard | None:
        response = await self._request(
            "GET", f"/boards/{board_id}", token=token, params={"fields": "name,url,closed"}
        )
        if response.status_code == 404:
            return None
        _raise_for_status(response)
        return self._board(response.json())

    async def board_lists(self, token: str, board_id: str) -> list[TrelloList]:
        data = await self._get_json(
            f"/boards/{board_id}/lists",
            token=token,
            params={"filter": "open", "fields": "name,pos"},
        )
        return [
            TrelloList(
                id=str(raw["id"]), name=str(raw.get("name", "")), pos=_to_float(raw.get("pos"))
            )
            for raw in data
        ]

    async def board_cards(self, token: str, board_id: str) -> list[TrelloCard]:
        data = await self._get_json(
            f"/boards/{board_id}/cards",
            token=token,
            params={"fields": _CARD_FIELDS, "limit": _CARD_LIMIT},
        )
        cards = [self._card(raw) for raw in data]
        return sorted(cards, key=lambda card: card.id)

    async def get_card(self, token: str, card_id: str) -> TrelloCard | None:
        response = await self._request(
            "GET", f"/cards/{card_id}", token=token, params={"fields": _CARD_FIELDS}
        )
        if response.status_code == 404:
            return None
        _raise_for_status(response)
        return self._card(response.json())

    async def register_webhook(
        self, token: str, board_id: str, callback_url: str, description: str
    ) -> str | None:
        response = await self._request(
            "POST",
            "/webhooks",
            token=token,
            params={"idModel": board_id, "callbackURL": callback_url, "description": description},
        )
        if not response.is_success:
            return None
        return str(response.json().get("id", "")) or None

    # ------------------------------------------------------------ helpers ---
    @staticmethod
    def _board(raw: dict[str, Any]) -> TrelloBoard:
        return TrelloBoard(
            id=str(raw["id"]),
            name=str(raw.get("name", "")),
            url=str(raw.get("url", "")),
            closed=bool(raw.get("closed", False)),
        )

    @staticmethod
    def _card(raw: dict[str, Any]) -> TrelloCard:
        labels = tuple(
            str(label.get("name", "")).strip()
            for label in raw.get("labels") or []
            if str(label.get("name", "")).strip()
        )
        return TrelloCard(
            id=str(raw["id"]),
            id_list=str(raw.get("idList", "")),
            name=str(raw.get("name", "")),
            desc=str(raw.get("desc", "")),
            url=str(raw.get("url", "")),
            closed=bool(raw.get("closed", False)),
            labels=labels,
            due=raw.get("due"),
        )

    async def _get_json(
        self, path: str, *, token: str, params: dict[str, Any] | None = None
    ) -> Any:
        response = await self._request("GET", path, token=token, params=params)
        _raise_for_status(response)
        return response.json()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        token: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        query = {"key": self._settings.trello_api_key, "token": token, **(params or {})}
        async with self._client() as client:
            return await client.request(method, f"{API_BASE}{path}", params=query)

    def _client(self) -> httpx.AsyncClient:
        if self._http is not None:
            return _SharedClient(self._http)
        return httpx.AsyncClient(timeout=30)


class _SharedClient:
    """Adapter para reutilizar um client externo (testes) sem fecha-lo."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, *args: object) -> None:
        return None


def _raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    detail = response.text[:300]
    raise TrelloApiError(response.status_code, detail)


def _to_float(raw: Any) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0
