"""API-token auth (ADR-0009 §3): bearer auth on guarded endpoints, scope
enforcement, revocation, and the session-only mint/list/revoke surface."""
from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from nylium.server import NyliumApp


def _mint(
    auth_client: TestClient, name: str = "agent", scope: str = "read-write"
) -> dict[str, Any]:
    response = auth_client.post("/api/auth/tokens", json={"name": name, "scope": scope})
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def _bearer(token: str) -> TestClient:
    client = TestClient(NyliumApp.create())
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def test_token_authenticates_guarded_endpoint(auth_client: TestClient) -> None:
    minted = _mint(auth_client)
    client = _bearer(str(minted["token"]))
    assert client.get("/api/types").status_code == 200
    assert client.get("/api/auth/me").json()["name"] == "owner"


def test_wrong_token_is_401() -> None:
    assert _bearer("not-a-real-token").get("/api/types").status_code == 401


def test_revoked_token_is_401(auth_client: TestClient) -> None:
    minted = _mint(auth_client)
    uuid = str(minted["uuid"])
    assert auth_client.delete(f"/api/auth/tokens/{uuid}").status_code == 200
    assert _bearer(str(minted["token"])).get("/api/types").status_code == 401


def test_read_scope_token_write_is_403(auth_client: TestClient) -> None:
    client = _bearer(str(_mint(auth_client, scope="read")["token"]))
    assert client.get("/api/types").status_code == 200  # read passes
    write = client.post(
        "/api/types",
        json={"name": "X", "plural_name": "Xs", "props": {"name": "String"}},
    )
    assert write.status_code == 403


def test_read_write_token_can_write(auth_client: TestClient) -> None:
    client = _bearer(str(_mint(auth_client, scope="read-write")["token"]))
    response = client.post(
        "/api/types",
        json={
            "name": "Book",
            "plural_name": "Books",
            "props": {"name": "String", "title": "String"},
        },
    )
    assert response.status_code == 201, response.text


def test_cookie_auth_still_works(auth_client: TestClient) -> None:
    assert auth_client.get("/api/types").status_code == 200
    assert auth_client.get("/api/auth/me").json()["name"] == "owner"


def test_list_never_returns_raw_token(auth_client: TestClient) -> None:
    minted = _mint(auth_client)
    raw = str(minted["token"])
    listed = auth_client.get("/api/auth/tokens")
    assert listed.status_code == 200
    for item in listed.json():
        assert "token" not in item
        assert raw not in str(item)


def test_token_cannot_mint_tokens(auth_client: TestClient) -> None:
    client = _bearer(str(_mint(auth_client)["token"]))
    response = client.post(
        "/api/auth/tokens", json={"name": "sneaky", "scope": "read-write"}
    )
    assert response.status_code == 403


def test_token_use_stamps_last_used(auth_client: TestClient) -> None:
    client = _bearer(str(_mint(auth_client, name="worker")["token"]))
    assert client.get("/api/types").status_code == 200
    worker = next(
        item for item in auth_client.get("/api/auth/tokens").json() if item["name"] == "worker"
    )
    assert worker["last_used_at"] is not None
