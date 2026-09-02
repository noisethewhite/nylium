"""End-to-end HTTP tests: FastAPI TestClient against a live Postgres.

Covers the wire contract both ways (request DTOs -> codec -> Api,
views -> JSON), the error-status mapping, and the SPA fallback.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from nylium.server import NyliumApp


class dsl:
    """Namespace for repeated request sequences (JSON is untyped at
    this boundary — hence Any, scoped to tests)."""

    @classmethod
    def create_type(
        cls, auth_client: TestClient, name: str, props: dict[str, str]
    ) -> dict[str, Any]:
        response = auth_client.post("/api/types", json={"name": name, "props": props})
        assert response.status_code == 201, response.text
        return response.json()  # type: ignore[no-any-return]

    @classmethod
    def create_object(
        cls, auth_client: TestClient, type_name: str, props: dict[str, Any]
    ) -> dict[str, Any]:
        response = auth_client.post(
            "/api/objects", json={"type_name": type_name, "props": props}
        )
        assert response.status_code == 201, response.text
        return response.json()  # type: ignore[no-any-return]

    @classmethod
    def create_book(cls, auth_client: TestClient, title: str) -> str:
        book = cls.create_object(auth_client, "Book", {"title": {"value": title}})
        return str(book["uuid"])


def test_types_roundtrip(auth_client: TestClient) -> None:
    created = dsl.create_type(
        auth_client, "Book", {"title": "String", "pages": "Integer"}
    )
    assert created["name"] == "Book"
    assert {prop["key"] for prop in created["props"]} == {"title", "pages"}

    names = {view["name"] for view in auth_client.get("/api/types").json()}
    assert "Book" in names

    fetched = auth_client.get("/api/types/Book")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Book"

    assert auth_client.get("/api/types/Nope").status_code == 404


def test_object_scalars_roundtrip(auth_client: TestClient) -> None:
    dsl.create_type(
        auth_client,
        "Book",
        {
            "title": "String",
            "pages": "Integer",
            "price": "Numeric",
            "available": "Boolean",
            "published": "Datetime",
        },
    )
    book = dsl.create_object(
        auth_client,
        "Book",
        {
            "title": {"value": "Dune"},
            "pages": {"value": 412},
            "price": {"value": 12.5},
            "available": {"value": True},
            "published": {"value": "1965-08-01T00:00:00"},
        },
    )
    props = book["props"]
    assert props["title"]["value"] == "Dune"
    assert props["pages"]["value"] == 412
    # Decimal crosses the wire losslessly as a string (pydantic JSON mode)
    assert props["price"]["value"] == "12.5"
    assert props["available"]["value"] is True
    assert str(props["published"]["value"]).startswith("1965-08-01T00:00:00")

    listed = auth_client.get("/api/objects", params={"type_name": "Book"})
    assert listed.status_code == 200
    assert [item["uuid"] for item in listed.json()] == [book["uuid"]]


def test_object_link_and_arrays(auth_client: TestClient) -> None:
    dsl.create_type(auth_client, "Book", {"title": "String"})
    dsl.create_type(
        auth_client,
        "Shelf",
        {
            "label": "String",
            "favorite": "Book",
            "books": "Array<Book>",
            "tags": "Array<String>",
        },
    )
    book_uuid = dsl.create_book(auth_client, "Dune")
    ref = {"ref": {"uuid": book_uuid, "type_name": "Book"}}
    shelf = dsl.create_object(
        auth_client,
        "Shelf",
        {
            "label": {"value": "sci-fi"},
            "favorite": ref,
            "books": {"items": [ref]},
            "tags": {"items": [{"value": "a"}, {"value": "b"}]},
        },
    )
    props = shelf["props"]
    assert props["favorite"]["ref"]["uuid"] == book_uuid
    assert props["books"]["items"][0]["ref"]["uuid"] == book_uuid
    assert [item["value"] for item in props["tags"]["items"]] == ["a", "b"]


def test_update_object_partial_and_array_semantics(auth_client: TestClient) -> None:
    dsl.create_type(
        auth_client, "Book", {"title": "String", "tags": "Array<String>"}
    )
    book = dsl.create_object(
        auth_client, "Book", {"tags": {"items": [{"value": "x"}]}}
    )
    uuid = str(book["uuid"])

    patched = auth_client.patch(
        f"/api/objects/{uuid}", json={"props": {"title": {"value": "Dune"}}}
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["props"]["title"]["value"] == "Dune"
    assert [i["value"] for i in patched.json()["props"]["tags"]["items"]] == ["x"]

    cleared = auth_client.patch(
        f"/api/objects/{uuid}", json={"props": {"tags": {"items": []}}}
    )
    assert cleared.status_code == 200
    assert cleared.json()["props"]["tags"]["items"] == []

    unset = auth_client.patch(
        f"/api/objects/{uuid}", json={"props": {"tags": {"items": None}}}
    )
    assert unset.status_code == 422


def test_wire_shape_mismatch_is_422(auth_client: TestClient) -> None:
    dsl.create_type(auth_client, "Book", {"title": "String"})
    dsl.create_type(auth_client, "Shelf", {"favorite": "Book"})
    response = auth_client.post(
        "/api/objects",
        json={
            "type_name": "Shelf",
            "props": {"favorite": {"value": "not-a-ref"}},
        },
    )
    assert response.status_code == 422


def test_unknown_keys_and_types_are_404(auth_client: TestClient) -> None:
    dsl.create_type(auth_client, "Book", {"title": "String"})
    unknown_prop = auth_client.post(
        "/api/objects",
        json={"type_name": "Book", "props": {"nope": {"value": "x"}}},
    )
    assert unknown_prop.status_code == 404
    unknown_type = auth_client.post("/api/objects", json={"type_name": "Nope"})
    assert unknown_type.status_code == 404


def test_delete_flows(auth_client: TestClient) -> None:
    dsl.create_type(auth_client, "Book", {"title": "String"})
    book_uuid = dsl.create_book(auth_client, "Dune")

    busy = auth_client.delete("/api/types/Book")
    assert busy.status_code == 409

    assert auth_client.delete(f"/api/objects/{book_uuid}").status_code == 204
    assert auth_client.get(f"/api/objects/{book_uuid}").status_code == 404

    assert auth_client.delete("/api/types/Book").status_code == 204
    assert auth_client.get("/api/types/Book").status_code == 404
    assert auth_client.delete("/api/types/Book").status_code == 404


def test_spa_fallback(
    auth_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index_text = "<html>spa</html>"
    asset_text = "console.log('x')"
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(index_text)
    (tmp_path / "assets" / "app.js").write_text(asset_text)
    monkeypatch.setenv("NYLIUM_WEB_DIST", str(tmp_path))
    spa = TestClient(NyliumApp.create())

    assert spa.get("/").text == index_text
    assert spa.get("/deep/auth_client/route").text == index_text
    assert spa.get("/assets/app.js").text == asset_text

    api_miss = spa.get("/api/definitely-not-a-route")
    assert api_miss.status_code == 404
    assert api_miss.headers["content-type"].startswith("application/json")
