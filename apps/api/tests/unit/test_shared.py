"""Testes do kernel compartilhado."""

from __future__ import annotations

import time
import uuid

from cadencia.platform.db import normalize_database_url
from cadencia.shared.domain import paginate
from cadencia.shared.ids import uuid7


def test_normalize_database_url_converts_libpq_params() -> None:
    neon = (
        "postgresql+asyncpg://user:pass@ep-x-pooler.us-east-1.aws.neon.tech/db"
        "?sslmode=require&channel_binding=require"
    )
    normalized = normalize_database_url(neon)
    assert "sslmode" not in normalized
    assert "channel_binding" not in normalized
    assert "ssl=require" in normalized
    # URLs que não são asyncpg (ex.: sqlite) passam intactas
    assert normalize_database_url("sqlite+aiosqlite:///./x.db") == "sqlite+aiosqlite:///./x.db"


def test_uuid7_is_version_7() -> None:
    value = uuid7()
    assert value.version == 7
    assert value.variant == uuid.RFC_4122


def test_uuid7_is_time_ordered() -> None:
    first = uuid7()
    time.sleep(0.005)
    second = uuid7()
    assert second.int > first.int


def test_paginate_window_and_has_more() -> None:
    items = list(range(10))
    window, has_more = paginate(items, limit=4, offset=0)
    assert window == [0, 1, 2, 3]
    assert has_more is True

    window, has_more = paginate(items, limit=4, offset=8)
    assert window == [8, 9]
    assert has_more is False
