"""Testes unitarios do conector Trello (sem rede)."""

from __future__ import annotations

import pytest

from cadencia.integrations.application.project_import import project_key_from_name
from cadencia.integrations.application.trello import (
    StartTrelloAuthorize,
    category_for_list,
    item_type_for_labels,
    parse_points_from_name,
)
from cadencia.platform.config import Settings
from cadencia.shared.errors import ValidationError
from cadencia.work.domain.value_objects import StatusCategory, WorkItemType


class FakeAuthorizeGateway:
    def build_authorize_url(self, return_url: str) -> str:
        return f"https://trello.com/1/authorize?key=abc&return_url={return_url}"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Fix login (5)", 5),
        ("Ajustar layout [8]", 8),
        ("Bug critico (4)", 3),  # snap para Fibonacci
        ("Sem pontos", None),
        ("Gigante (21)", 13),  # snap para o teto do Fibonacci
        ("Valor (0)", None),
    ],
)
def test_parse_points_from_name(name: str, expected: int | None) -> None:
    assert parse_points_from_name(name) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Done", StatusCategory.DONE),
        ("Concluído", StatusCategory.DONE),
        ("Deploy", StatusCategory.DONE),
        ("In Progress", StatusCategory.IN_PROGRESS),
        ("Code Review", StatusCategory.IN_PROGRESS),
        ("Em andamento", StatusCategory.IN_PROGRESS),
        ("Backlog", StatusCategory.TODO),
        ("A fazer", StatusCategory.TODO),
    ],
)
def test_category_for_list(name: str, expected: StatusCategory) -> None:
    assert category_for_list(name) is expected


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        (("Bug",), WorkItemType.BUG),
        (("bug", "urgente"), WorkItemType.BUG),
        (("Epic",), WorkItemType.EPIC),
        (("Story",), WorkItemType.STORY),
        (("História",), WorkItemType.STORY),
        ((), WorkItemType.TASK),
        (("Marketing",), WorkItemType.TASK),
    ],
)
def test_item_type_for_labels(labels: tuple[str, ...], expected: WorkItemType) -> None:
    assert item_type_for_labels(labels) is expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Produto", "PRODUTO"),
        ("Meu Board Legal!", "MEUBOARDLE"),
        ("x", "TX"),
        ("123", "T123"),
    ],
)
def test_project_key_from_name(name: str, expected: str) -> None:
    assert project_key_from_name(name) == expected


async def test_start_authorize_requires_api_key() -> None:
    settings = Settings(jwt_secret="x" * 32, trello_api_key="")
    with pytest.raises(ValidationError, match="TRELLO_API_KEY"):
        await StartTrelloAuthorize(FakeAuthorizeGateway(), settings).execute()  # type: ignore[arg-type]


async def test_start_authorize_uses_return_url() -> None:
    settings = Settings(
        jwt_secret="x" * 32,
        trello_api_key="key-123",
        web_base_url="https://app.example",
    )
    url = await StartTrelloAuthorize(FakeAuthorizeGateway(), settings).execute()  # type: ignore[arg-type]
    assert "key=abc" in url
    assert "return_url=https://app.example/integrations/trello/callback" in url
