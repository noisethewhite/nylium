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
        cls,
        auth_client: TestClient,
        name: str,
        props: dict[str, str],
        plural_name: str | None = None,
    ) -> dict[str, Any]:
        response = auth_client.post(
            "/api/types",
            json={
                "name": name,
                "plural_name": plural_name if plural_name is not None else f"{name}s",
                "props": props,
            },
        )
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
        auth_client, "Book", {"name": "String", "title": "String", "pages": "Integer"}
    )
    assert created["name"] == "Book"
    assert created["plural_name"] == "Books"
    assert {prop["key"] for prop in created["props"]} == {"name", "title", "pages"}

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
            "name": "String",
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


def test_calendar_scalar_family_roundtrip(auth_client: TestClient) -> None:
    dsl.create_type(
        auth_client,
        "Event",
        {
            "name": "String",
            "on": "Date",
            "at": "Time",
            "starts": "Datetime",
            "birthday": "MonthDay",
            "alarm": "MonthDayTime",
        },
    )
    event = dsl.create_object(
        auth_client,
        "Event",
        {
            "on": {"value": "2026-09-03"},
            "at": {"value": "14:30"},
            "starts": {"value": "2026-09-03T14:30:00"},
            "birthday": {"value": "02-29"},
            "alarm": {"value": "12-25T08:00"},
        },
    )
    props = event["props"]
    assert props["on"]["value"] == "2026-09-03"
    assert str(props["at"]["value"]).startswith("14:30")
    assert str(props["starts"]["value"]).startswith("2026-09-03T14:30:00")
    assert props["birthday"]["value"] == "02-29"
    assert props["alarm"]["value"] == "12-25T08:00"

    # impossible calendar stamps are rejected at the codec
    bad = auth_client.post(
        "/api/objects",
        json={"type_name": "Event", "props": {"birthday": {"value": "02-31"}}},
    )
    assert bad.status_code == 422


def test_object_link_and_arrays(auth_client: TestClient) -> None:
    dsl.create_type(auth_client, "Book", {"name": "String", "title": "String"})
    dsl.create_type(
        auth_client,
        "Shelf",
        {
            "name": "String",
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
        auth_client, "Book", {"name": "String", "title": "String", "tags": "Array<String>"}
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
    dsl.create_type(auth_client, "Book", {"name": "String", "title": "String"})
    dsl.create_type(auth_client, "Shelf", {"name": "String", "favorite": "Book"})
    response = auth_client.post(
        "/api/objects",
        json={
            "type_name": "Shelf",
            "props": {"favorite": {"value": "not-a-ref"}},
        },
    )
    assert response.status_code == 422


def test_unknown_keys_and_types_are_404(auth_client: TestClient) -> None:
    dsl.create_type(auth_client, "Book", {"name": "String", "title": "String"})
    unknown_prop = auth_client.post(
        "/api/objects",
        json={"type_name": "Book", "props": {"nope": {"value": "x"}}},
    )
    assert unknown_prop.status_code == 404
    unknown_type = auth_client.post("/api/objects", json={"type_name": "Nope"})
    assert unknown_type.status_code == 404


def test_delete_flows(auth_client: TestClient) -> None:
    dsl.create_type(auth_client, "Book", {"name": "String", "title": "String"})
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


def test_reorder_props_endpoint(auth_client: TestClient) -> None:
    dsl.create_type(
        auth_client,
        "Track",
        {"name": "String", "title": "String", "bpm": "Integer", "live": "Boolean"},
    )
    response = auth_client.patch(
        "/api/types/Track/props-order", json={"keys": ["name", "bpm", "live", "title"]}
    )
    assert response.status_code == 200, response.text
    assert [prop["key"] for prop in response.json()["props"]] == [
        "name",
        "bpm",
        "live",
        "title",
    ]
    reloaded = auth_client.get("/api/types/Track")
    assert [prop["key"] for prop in reloaded.json()["props"]] == [
        "name",
        "bpm",
        "live",
        "title",
    ]


def test_reorder_props_moving_name_is_422(auth_client: TestClient) -> None:
    dsl.create_type(
        auth_client, "Track", {"name": "String", "title": "String", "bpm": "Integer"}
    )
    response = auth_client.patch(
        "/api/types/Track/props-order", json={"keys": ["title", "name", "bpm"]}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation"


def test_create_type_without_name_is_422(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/types",
        json={"name": "Track", "plural_name": "Tracks", "props": {"title": "String"}},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation"


def test_reorder_props_mismatch_is_409(auth_client: TestClient) -> None:
    dsl.create_type(auth_client, "Track", {"name": "String", "title": "String", "bpm": "Integer"})
    response = auth_client.patch(
        "/api/types/Track/props-order", json={"keys": ["title", "nope"]}
    )
    assert response.status_code == 409
    assert set(response.json()["error"]) == {"code", "message"}
    assert response.json()["error"]["code"] == "conflict"


def test_error_body_shape(auth_client: TestClient) -> None:
    missing = auth_client.get("/api/types/Nope")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
    malformed = auth_client.post("/api/types", json={"props": "not-a-dict"})
    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "validation"


def test_unexpected_error_is_500_json(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nylium.api import Api

    def boom(name: str) -> None:
        raise RuntimeError("boom")

    # ServerErrorMiddleware always re-raises after answering, so this
    # check needs a client that doesn't escalate server exceptions.
    import secrets

    from nylium.auth.sessions import sessions
    from nylium.database.tables import AuthCredentials, AuthUsers
    from nylium.server import NyliumApp

    user = AuthUsers.create("boom-owner")
    AuthCredentials.register(user.uuid, secrets.token_bytes(32), b"pk", 0, "")
    client = TestClient(NyliumApp.create(), raise_server_exceptions=False)
    client.cookies.set(sessions.COOKIE_NAME, sessions.issue(user.uuid))
    monkeypatch.setattr(Api, "get_type", boom)
    response = client.get("/api/types/Anything")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal", "message": "internal server error"}
    }


def test_unauthenticated_error_shape() -> None:
    response = TestClient(NyliumApp.create()).get("/api/types")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def sync_draft(schema: dict[str, Any], drop=(), rename=None, retype=None, add=()):
    """Wire version of the api-layer draft builder."""
    rename = rename or {}
    retype = retype or {}
    items = [
        {
            "uuid": prop["uuid"],
            "key": rename.get(prop["key"], prop["key"]),
            "value_type": retype.get(prop["key"], prop["value_type"]),
        }
        for prop in schema["props"]
        if prop["key"] not in drop
    ]
    return items + [{"uuid": None, "key": key, "value_type": vt} for key, vt in add]


def test_sync_props_endpoint_roundtrip(auth_client: TestClient) -> None:
    schema = dsl.create_type(
        auth_client, "Note", {"name": "String", "body": "String", "priority": "Integer"}
    )
    note = dsl.create_object(
        auth_client,
        "Note",
        {"name": {"value": "n1"}, "body": {"value": "hello"}, "priority": {"value": 5}},
    )
    response = auth_client.put(
        "/api/types/Note/props",
        json={
            "props": sync_draft(
                schema,
                rename={"body": "text"},
                retype={"priority": "String"},
                add=[("mood", "String")],
            )
        },
    )
    assert response.status_code == 200, response.text
    assert [prop["key"] for prop in response.json()["props"]] == [
        "name", "text", "priority", "mood",
    ]
    reloaded = auth_client.get(f"/api/objects/{note['uuid']}").json()
    assert reloaded["props"]["text"] == {"value": "hello"}  # rename keeps data
    assert reloaded["props"]["priority"] == {"value": None}  # retype purges
    assert reloaded["props"]["mood"] == {"value": None}  # new prop = Null

    deleting = auth_client.put(
        "/api/types/Note/props",
        json={"props": sync_draft(response.json(), drop=("mood",))},
    )
    assert deleting.status_code == 200, deleting.text
    gone = auth_client.get(f"/api/objects/{note['uuid']}").json()
    assert "mood" not in gone["props"]


def test_sync_props_tampering_name_is_422(auth_client: TestClient) -> None:
    schema = dsl.create_type(auth_client, "Note", {"name": "String", "body": "String"})
    for draft in (
        sync_draft(schema, drop=("name",)),
        sync_draft(schema, rename={"name": "title"}),
        sync_draft(schema, retype={"name": "Integer"}),
    ):
        response = auth_client.put("/api/types/Note/props", json={"props": draft})
        assert response.status_code == 422, response.text
        assert response.json()["error"]["code"] == "validation"


def test_sync_props_duplicate_keys_is_422(auth_client: TestClient) -> None:
    schema = dsl.create_type(auth_client, "Note", {"name": "String", "body": "String"})
    response = auth_client.put(
        "/api/types/Note/props",
        json={"props": sync_draft(schema, add=[("body", "Integer")])},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation"


def test_update_type_endpoint(auth_client: TestClient) -> None:
    dsl.create_type(auth_client, "Note", {"name": "String", "body": "String"})
    response = auth_client.patch("/api/types/Note", json={"name": "Memo", "plural_name": "Memos"})
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Memo"
    assert response.json()["plural_name"] == "Memos"
    assert auth_client.get("/api/types/Note").status_code == 404
    assert auth_client.get("/api/types/Memo").status_code == 200


def test_update_type_guards(auth_client: TestClient) -> None:
    dsl.create_type(auth_client, "Note", {"name": "String"})
    collision = auth_client.patch("/api/types/Note", json={"name": "String"})
    assert collision.status_code == 409
    builtin = auth_client.patch("/api/types/String", json={"name": "Text"})
    assert builtin.status_code == 422
    missing = auth_client.patch("/api/types/Nope", json={"name": "Memo"})
    assert missing.status_code == 404
