"""Fixtures compartilhadas: app com SQLite em memória e client ASGI."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from typing import Any

os.environ.setdefault("CADENCIA_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("CADENCIA_JWT_SECRET", "test-secret-do-not-use-in-prod")
os.environ.setdefault("CADENCIA_ENVIRONMENT", "test")
os.environ.setdefault("CADENCIA_REGISTRATION_MODE", "open")
os.environ.setdefault("CADENCIA_REGISTER_MAX_ATTEMPTS", "10000")
os.environ.setdefault("CADENCIA_LOGIN_MAX_ATTEMPTS", "10000")
os.environ.setdefault("CADENCIA_REFRESH_MAX_ATTEMPTS", "10000")

logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

import httpx  # noqa: E402
import pytest  # noqa: E402

from cadencia.identity.infrastructure import orm as identity_orm  # noqa: E402, F401
from cadencia.integrations.infrastructure import orm as integrations_orm  # noqa: E402, F401
from cadencia.main import create_app  # noqa: E402
from cadencia.platform import orm as platform_orm  # noqa: E402, F401
from cadencia.platform.db import Base  # noqa: E402
from cadencia.work.infrastructure import orm as work_orm  # noqa: E402, F401

app = create_app()


@pytest.fixture
def api_app() -> Any:
    """A MESMA instância usada pelo client (evita import de tests.conftest duplicar o app)."""
    return app


@pytest.fixture(autouse=True)
async def _fresh_database() -> None:
    engine = app.state.engine
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    return


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


DEMO = {
    "email": "owner@example.com",
    "name": "Owner",
    "password": "super-secret-1",
}


async def register_and_login(
    client: httpx.AsyncClient, *, email: str | None = None
) -> dict[str, str]:
    payload = {**DEMO, "email": email or DEMO["email"]}
    register = await client.post("/api/v1/auth/register", json=payload)
    assert register.status_code == 201, register.text
    login = await client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    return await register_and_login(client)


async def create_workspace(
    client: httpx.AsyncClient, headers: dict[str, str], *, name: str = "Acme"
) -> dict[str, Any]:
    response = await client.post("/api/v1/workspaces", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
async def workspace(client: httpx.AsyncClient, auth_headers: dict[str, str]) -> dict[str, Any]:
    return await create_workspace(client, auth_headers)


async def create_project(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    workspace_id: str,
    *,
    key: str = "APP",
    name: str = "App Mobile",
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        json={"name": name, "key": key},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()
