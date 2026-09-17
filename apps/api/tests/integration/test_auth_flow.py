"""Fluxo de autenticacao ponta a ponta na API (RN-03, RN-04, rotacao de refresh)."""

from __future__ import annotations

import httpx
from tests.conftest import DEMO

PROBLEM = "application/problem+json"


async def test_register_login_and_me(client: httpx.AsyncClient) -> None:
    register = await client.post("/api/v1/auth/register", json=DEMO)
    assert register.status_code == 201
    assert register.json()["email"] == DEMO["email"]

    login = await client.post(
        "/api/v1/auth/login", json={"email": DEMO["email"], "password": DEMO["password"]}
    )
    assert login.status_code == 200
    access = login.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["email"] == DEMO["email"]


async def test_duplicate_email_conflicts(client: httpx.AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=DEMO)
    again = await client.post("/api/v1/auth/register", json=DEMO)
    assert again.status_code == 409
    assert again.headers["content-type"].startswith(PROBLEM)
    assert again.json()["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_wrong_password_returns_401_problem(client: httpx.AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=DEMO)
    response = await client.post(
        "/api/v1/auth/login", json={"email": DEMO["email"], "password": "senha-errada-1"}
    )
    assert response.status_code == 401
    assert response.headers["content-type"].startswith(PROBLEM)
    assert response.json()["code"] == "INVALID_CREDENTIALS"


async def test_weak_password_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/auth/register", json={**DEMO, "password": "curta"})
    assert response.status_code == 422


async def test_refresh_rotation_and_reuse_detection(client: httpx.AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=DEMO)
    login = await client.post(
        "/api/v1/auth/login", json={"email": DEMO["email"], "password": DEMO["password"]}
    )
    original_cookie = login.cookies.get("cadencia_refresh")
    assert original_cookie

    def cookie_header(value: str) -> dict[str, str]:
        return {"cookie": f"cadencia_refresh={value}"}

    rotated = await client.post("/api/v1/auth/refresh", headers=cookie_header(original_cookie))
    assert rotated.status_code == 200
    assert rotated.json()["access_token"]
    rotated_cookie = rotated.cookies.get("cadencia_refresh")
    assert rotated_cookie is not None
    assert rotated_cookie != original_cookie

    # Replay do token antigo: reuse detection revoga a familia inteira.
    replay = await client.post("/api/v1/auth/refresh", headers=cookie_header(original_cookie))
    assert replay.status_code == 401
    assert replay.json()["code"] == "SESSION_REUSE_DETECTED"

    # A familia revogada nao emite mais tokens, nem com o cookie rotacionado.
    after = await client.post("/api/v1/auth/refresh", headers=cookie_header(rotated_cookie))
    assert after.status_code == 401


async def test_logout_revokes_session(client: httpx.AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=DEMO)
    await client.post(
        "/api/v1/auth/login", json={"email": DEMO["email"], "password": DEMO["password"]}
    )
    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    refresh = await client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 401


async def test_unauthenticated_requests_are_rejected(client: httpx.AsyncClient) -> None:
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401
    assert me.json()["code"] == "MISSING_TOKEN"
    workspaces = await client.get("/api/v1/workspaces")
    assert workspaces.status_code == 401
