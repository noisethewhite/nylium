"""Passkey auth: 401 guard, bootstrap gating, session lifecycle.

Real passkey bytes can't be faked without an authenticator, so
finish-ceremony tests cover rejection paths only; the session lifecycle
is exercised with tokens issued directly.
"""
from __future__ import annotations

import secrets

import pytest
from fastapi.testclient import TestClient

from nylium.auth.sessions import sessions
from nylium.tables import auth_credentials, auth_users
from nylium.server import NyliumApp


@pytest.fixture()
def client() -> TestClient:
    return TestClient(NyliumApp.create())


def _plant_owner() -> str:
    user = next(auth_users.where(name="owner"), None) or auth_users.create("owner")
    auth_credentials.create(user.uuid, secrets.token_bytes(32), b"pk", 0, "")
    return sessions.issue(user.uuid)


def test_api_requires_auth(client: TestClient) -> None:
    assert client.get("/api/types").status_code == 401
    assert client.get("/api/objects").status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_register_bootstrap_gating(client: TestClient) -> None:
    unnamed = client.post("/api/auth/register/start", json={})
    assert unnamed.status_code == 422  # first passkey needs a user name

    options = client.post("/api/auth/register/start", json={"name": "owner"})
    assert options.status_code == 200
    assert options.json()["rp"]["name"] == "nylium"

    _plant_owner()  # a credential exists now -> registration closes
    closed = client.post("/api/auth/register/start", json={"name": "intruder"})
    assert closed.status_code == 401


def test_register_finish_rejects_garbage(client: TestClient) -> None:
    assert client.post("/api/auth/register/start", json={"name": "owner"})
    bad = client.post("/api/auth/register/finish", content=b"{}")
    assert bad.status_code == 401
    worse = client.post("/api/auth/register/finish", content=b"not json")
    assert worse.status_code == 401


def test_login_start_shape(client: TestClient) -> None:
    response = client.post("/api/auth/login/start")
    assert response.status_code == 200
    assert "challenge" in response.json()


def test_login_finish_unknown_credential(client: TestClient) -> None:
    assert client.post("/api/auth/login/start").status_code == 200
    body = {"rawId": "AAAA", "response": {"clientDataJSON": "AAAA"}}
    assert client.post("/api/auth/login/finish", json=body).status_code == 401


def test_session_lifecycle(client: TestClient) -> None:
    client.cookies.set(sessions.COOKIE_NAME, _plant_owner())
    assert client.get("/api/auth/me").json()["name"] == "owner"
    assert client.get("/api/types").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401
