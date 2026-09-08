"""End-to-end HTTP tests: FastAPI TestClient against a live Postgres.

Covers the wire contract both ways (request DTOs -> codec -> Api,
views -> JSON), the error-status mapping, and the SPA fallback.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from nylium.objects.wscalar import WColor
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
        icon: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "plural_name": plural_name if plural_name is not None else f"{name}s",
            "props": props,
        }
        if icon is not None:
            payload["icon"] = icon
        if color is not None:
            payload["color"] = color
        response = auth_client.post("/api/types", json=payload)
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


def test_file_types_immutable_over_http(auth_client: TestClient) -> None:
    from nylium.objects.wfile import WFile

    WFile.ensure_builtins()
    assert auth_client.delete("/api/types/File").status_code == 422
    assert auth_client.delete("/api/types/Image").status_code == 422
    assert auth_client.delete("/api/types/Document").status_code == 422


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
    from nylium.tables import auth_credentials, auth_users
    from nylium.server import NyliumApp

    user = auth_users.create("boom-owner")
    auth_credentials.create(user.uuid, secrets.token_bytes(32), b"pk", 0, "")
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
    assert reloaded["props"]["text"] == {"value": "hello", "unit": None}  # rename keeps data
    assert reloaded["props"]["priority"] == {"value": None, "unit": None}  # retype purges
    assert reloaded["props"]["mood"] == {"value": None, "unit": None}  # new prop = Null

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


def test_type_icon_and_color_over_http(auth_client):
    dsl.create_type(auth_client, "Tagged", {"name": "String"}, icon="star", color="#e5534b")
    view = auth_client.get("/api/types/Tagged").json()
    assert (view["icon"], view["color"]) == ("star", "#e5534b")
    response = auth_client.patch("/api/types/Tagged", json={"icon": "heart", "color": "#e275ad"})
    assert response.status_code == 200
    assert (response.json()["icon"], response.json()["color"]) == ("heart", "#e275ad")
    builtin = auth_client.get("/api/types/String").json()
    assert (builtin["icon"], builtin["color"]) == ("text_fields", "#9e9e9e")


def test_enum_over_http(auth_client: TestClient) -> None:
    created = auth_client.post(
        "/api/enums", json={"name": "Status", "options": ["open", "closed"]}
    )
    assert created.status_code == 201, created.text
    view = created.json()
    assert view["kind"] == "enum"
    assert [option["value"] for option in view["enum_options"]] == ["open", "closed"]
    assert view["props"] == []

    dsl.create_type(auth_client, "Ticket", {"name": "String", "status": "Status"})
    ticket = dsl.create_object(
        auth_client, "Ticket", {"name": {"value": "t1"}, "status": {"value": "open"}}
    )
    assert ticket["props"]["status"]["value"] == "open"

    bad = auth_client.post(
        "/api/objects",
        json={"type_name": "Ticket", "props": {"status": {"value": "bogus"}}},
    )
    assert bad.status_code == 422

    open_uuid = next(
        option["uuid"] for option in view["enum_options"] if option["value"] == "open"
    )
    synced = auth_client.put(
        "/api/enums/Status/options",
        json={"options": [{"uuid": open_uuid, "value": "in progress"}]},
    )
    assert synced.status_code == 200, synced.text
    assert [o["value"] for o in synced.json()["enum_options"]] == ["in progress"]
    reloaded = auth_client.get(f"/api/objects/{ticket['uuid']}").json()
    assert reloaded["props"]["status"]["value"] == "in progress"

    delete_in_use = auth_client.put("/api/enums/Status/options", json={"options": []})
    assert delete_in_use.status_code == 409


def test_unit_over_http(auth_client: TestClient) -> None:
    created = auth_client.post(
        "/api/units",
        json={
            "name": "Temperature",
            "base": "°C",
            "secondaries": [{"name": "°F", "multiplier": 1.8, "offset": 32}],
        },
    )
    assert created.status_code == 201, created.text
    view = created.json()
    assert view["kind"] == "unit"
    assert [(p["name"], p["is_base"]) for p in view["unit_parts"]] == [
        ("°C", True), ("°F", False),
    ]

    dsl.create_type(auth_client, "Oven", {"name": "String", "temp": "Numeric<Temperature>"})
    oven = dsl.create_object(
        auth_client, "Oven", {"name": {"value": "o1"}, "temp": {"value": 32, "unit": "°F"}}
    )
    assert oven["props"]["temp"] == {"value": "32.0", "unit": "°F"}  # Decimal → str on the wire

    bogus = auth_client.post(
        "/api/objects",
        json={"type_name": "Oven", "props": {"temp": {"value": 1, "unit": "kelvin"}}},
    )
    assert bogus.status_code == 422

    f_uuid = next(p["uuid"] for p in view["unit_parts"] if p["name"] == "°F")
    c_uuid = next(p["uuid"] for p in view["unit_parts"] if p["name"] == "°C")
    synced = auth_client.put(
        "/api/units/Temperature/parts",
        json={"parts": [
            {"uuid": c_uuid, "name": "°C", "multiplier": 1, "offset": 0, "is_base": True},
            {"uuid": f_uuid, "name": "fahrenheit", "multiplier": 1.8, "offset": 32, "is_base": False},
        ]},
    )
    assert synced.status_code == 200, synced.text
    reloaded = auth_client.get(f"/api/objects/{oven['uuid']}").json()
    assert reloaded["props"]["temp"]["unit"] == "fahrenheit"

    delete_in_use = auth_client.put(
        "/api/units/Temperature/parts",
        json={"parts": [
            {"uuid": c_uuid, "name": "°C", "multiplier": 1, "offset": 0, "is_base": True},
        ]},
    )
    assert delete_in_use.status_code == 409


def test_embedded_over_http(auth_client: TestClient) -> None:
    """ADR-0004 over the wire: embedded type create flag, inline draft
    both ways, guards, visibility."""
    created = auth_client.post(
        "/api/types",
        json={
            "name": "ContactDetails",
            "plural_name": "ContactDetails",
            "props": {"name": "String", "email": "String"},
            "embedded": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["embedded"] is True

    dsl.create_type(
        auth_client, "Person", {"name": "String", "contact": "ContactDetails"}
    )
    # standalone create of an embedded type is 422
    standalone = auth_client.post(
        "/api/objects",
        json={"type_name": "ContactDetails", "props": {"name": {"value": "x"}}},
    )
    assert standalone.status_code == 422

    person = dsl.create_object(
        auth_client,
        "Person",
        {
            "name": {"value": "Vasya"},
            "contact": {
                "uuid": None,
                "type_name": "ContactDetails",
                "props": {"email": {"value": "v@x.com"}},
            },
        },
    )
    contact = person["props"]["contact"]
    assert contact["uuid"] is not None
    assert contact["type_name"] == "ContactDetails"
    assert contact["props"]["email"]["value"] == "v@x.com"
    assert contact["props"]["name"]["value"] == "Vasya → contact"

    # embedded children never list standalone
    listed = auth_client.get("/api/objects", params={"type_name": "ContactDetails"})
    assert listed.status_code == 200
    assert listed.json() == []

    # direct writes to the child are refused — edit through the owner
    direct = auth_client.patch(
        f"/api/objects/{contact['uuid']}",
        json={"props": {"email": {"value": "other@x.com"}}},
    )
    assert direct.status_code == 422

    # parent rename regenerates the child name
    renamed = auth_client.patch(
        f"/api/objects/{person['uuid']}", json={"props": {"name": {"value": "Petya"}}}
    )
    assert renamed.status_code == 200
    assert renamed.json()["props"]["contact"]["props"]["name"]["value"] == "Petya → contact"

    # an empty draft clears the prop and deletes the child
    cleared = auth_client.patch(
        f"/api/objects/{person['uuid']}",
        json={"props": {"contact": {"uuid": None, "type_name": "ContactDetails", "props": {}}}},
    )
    assert cleared.status_code == 200
    assert cleared.json()["props"]["contact"]["uuid"] is None
    gone = auth_client.get(f"/api/objects/{contact['uuid']}")
    assert gone.status_code == 404


def test_tags_over_http(auth_client: TestClient) -> None:
    """ADR-0005 over the wire: array membership projects back onto the
    member object as a derived tag, named after the owner and prop."""
    dsl.create_type(auth_client, "Book", {"name": "String", "title": "String"})
    dsl.create_type(
        auth_client, "Shelf", {"name": "String", "label": "String", "books": "Array<Book>"}
    )
    book = dsl.create_object(auth_client, "Book", {"name": {"value": "Dune"}})
    book_uuid = str(book["uuid"])
    ref = {"ref": {"uuid": book_uuid, "type_name": "Book"}}
    shelf = dsl.create_object(
        auth_client,
        "Shelf",
        {"name": {"value": "Sci-Fi"}, "books": {"items": [ref]}},
    )

    fetched = auth_client.get(f"/api/objects/{book_uuid}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["tags"] == [
        {
            "owner_uuid": str(shelf["uuid"]),
            "owner_name": "Sci-Fi",
            "prop_key": "books",
            "name": "Sci-Fi → books",
            "color": WColor.DEFAULT,
        }
    ]

    # removing the membership removes the tag on the member's next read
    cleared = auth_client.patch(
        f"/api/objects/{shelf['uuid']}", json={"props": {"books": {"items": []}}}
    )
    assert cleared.status_code == 200
    refetched = auth_client.get(f"/api/objects/{book_uuid}")
    assert refetched.status_code == 200
    assert refetched.json()["tags"] == []


def test_formulas_over_http(auth_client: TestClient) -> None:
    """ADR-0005 over the wire: formulas ride create_type/sync_props and
    surface on Type; invalid formulas are 422."""
    dsl.create_type(auth_client, "Item", {"name": "String", "price": "Numeric"})
    created = auth_client.post(
        "/api/types",
        json={
            "name": "Receipt",
            "plural_name": "Receipts",
            "props": {
                "name": "String",
                "items": "Array<Item>",
                "total": "Numeric",
            },
            "formulas": {"total": "SUM(items.price) * 1.21"},
        },
    )
    assert created.status_code == 201, created.text
    by_key = {prop["key"]: prop for prop in created.json()["props"]}
    assert by_key["total"]["formula"] == "SUM(items.price) * 1.21"
    assert by_key["items"]["formula"] is None

    invalid = auth_client.post(
        "/api/types",
        json={
            "name": "BadReceipt",
            "plural_name": "BadReceipts",
            "props": {
                "name": "String",
                "items": "Array<Item>",
                "total": "Numeric",
            },
            "formulas": {"total": "SUM(items.weight)"},
        },
    )
    assert invalid.status_code == 422


def test_formulas_eval_over_http(auth_client: TestClient) -> None:
    """Read-time evaluation over the wire: a computed prop renders its
    value, writes into it are 422, and the value tracks live members."""
    dsl.create_type(auth_client, "Item", {"name": "String", "price": "Numeric"})
    created = auth_client.post(
        "/api/types",
        json={
            "name": "Receipt",
            "plural_name": "Receipts",
            "props": {
                "name": "String",
                "lines": "Array<Item>",
                "total": "Numeric",
                "count": "Integer",
            },
            "formulas": {"total": "SUM(lines.price)", "count": "COUNT(lines)"},
        },
    )
    assert created.status_code == 201, created.text

    def item(name: str, price: str):
        body = dsl.create_object(
            auth_client,
            "Item",
            {"name": {"value": name}, "price": {"value": price}},
        )
        return {"ref": {"uuid": str(body["uuid"]), "type_name": "Item"}}

    receipt = dsl.create_object(
        auth_client,
        "Receipt",
        {
            "name": {"value": "R1"},
            "lines": {"items": [item("a", "10.5"), item("b", "2")]},
        },
    )
    fetched = auth_client.get(f"/api/objects/{receipt['uuid']}")
    assert fetched.status_code == 200, fetched.text
    props = fetched.json()["props"]
    assert props["total"] == {"value": "12.5", "unit": None}
    assert props["count"] == {"value": 2, "unit": None}

    # computed props are read-only over the wire
    blocked = auth_client.patch(
        f"/api/objects/{receipt['uuid']}", json={"props": {"total": {"value": "1"}}}
    )
    assert blocked.status_code == 422

    # ...and the value re-evaluates on every read
    updated = auth_client.patch(
        f"/api/objects/{receipt['uuid']}", json={"props": {"lines": {"items": []}}}
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["props"]["total"] == {"value": "0", "unit": None}




def test_files_over_http(auth_client: TestClient) -> None:
    """Upload/download roundtrip over the wire (ADR-0008): builtin file
    types are boot-seeded by NyliumApp.create, blobs live under the
    test FILES_DIR, delete cascades to disk."""
    from nylium.objects.wfile import WFile

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16

    # upload an image
    up = auth_client.post(
        "/api/files",
        params={"type_name": "Image"},
        files={"file": ("icon.png", png, "image/png")},
    )
    assert up.status_code == 201, up.text
    obj = up.json()
    assert obj["type_name"] == "Image"
    assert obj["name"] == "icon.png"

    # download streams the bytes back with the original mime + filename
    dl = auth_client.get(f"/api/files/{obj['uuid']}/download")
    assert dl.status_code == 200, dl.text
    assert dl.content == png
    assert dl.headers["content-type"].startswith("image/png")
    assert "icon.png" in dl.headers["content-disposition"]

    # MIME policy: Image rejects non-image bytes
    bad = auth_client.post(
        "/api/files",
        params={"type_name": "Image"},
        files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert bad.status_code == 422, bad.text

    # File takes anything
    anyfile = auth_client.post(
        "/api/files",
        params={"type_name": "File"},
        files={"file": ("blob.bin", b"junk", "application/x-junk")},
    )
    assert anyfile.status_code == 201, anyfile.text

    # rename-safe: patch the display name, bytes stay
    rename = auth_client.patch(
        f"/api/files/{obj['uuid']}", json={"name": "renamed.png"}
    )
    assert rename.status_code == 200, rename.text
    assert auth_client.get(f"/api/files/{obj['uuid']}/download").content == png

    # delete cascades: row gone, blob gone
    deleted = auth_client.delete(f"/api/files/{obj['uuid']}")
    assert deleted.status_code == 204, deleted.text
    assert not WFile.blob_path(obj["uuid"]).exists()
    assert auth_client.get(f"/api/files/{obj['uuid']}").status_code == 404

    # unknown uuid is a 404, not a 500
    from uuid import uuid4

    assert auth_client.get(f"/api/files/{uuid4()}").status_code == 404


def test_img_icon_over_http(auth_client: TestClient) -> None:
    """img:<uuid> type icons validate against live Image files and
    fall back to the default glyph when the image is deleted."""
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    up = auth_client.post(
        "/api/files",
        params={"type_name": "Image"},
        files={"file": ("icon.png", png, "image/png")},
    )
    assert up.status_code == 201, up.text
    icon = f"img:{up.json()['uuid']}"

    created = dsl.create_type(auth_client, "Book", {"name": "String"}, icon=icon)
    assert created["icon"] == icon

    from uuid import uuid4

    dead = auth_client.post(
        "/api/types",
        json={"name": "Ghost", "plural_name": "Ghosts", "props": {"name": "String"}, "icon": f"img:{uuid4()}"},
    )
    assert dead.status_code == 422, dead.text

    deleted = auth_client.delete(f"/api/files/{up.json()['uuid']}")
    assert deleted.status_code == 204
    assert auth_client.get("/api/types/Book").json()["icon"] == "inventory_2"


def _function_draft(input_type, output_type, name, input_object_uuid, nodes, edges):
    """Wire shape of a Create/Update function draft (ADR-0007)."""
    return {
        "input_type": input_type,
        "output_type": output_type,
        "name": name,
        "input_object_uuid": input_object_uuid,
        "nodes": nodes,
        "edges": edges,
    }


def test_function_lifecycle_over_http(auth_client: TestClient) -> None:
    from uuid import uuid4

    dsl.create_type(
        auth_client, "Invoice", {"name": "String", "total": "Numeric", "tax": "Numeric"}
    )
    dsl.create_type(auth_client, "Report", {"name": "String", "amount": "Numeric"})
    inv = dsl.create_object(
        auth_client,
        "Invoice",
        {"name": {"value": "i1"}, "total": {"value": "100"}, "tax": {"value": "5"}},
    )

    n = uuid4()
    created = auth_client.post(
        "/api/functions",
        json=_function_draft(
            "Invoice",
            "Numeric",
            "total passthrough",
            str(inv["uuid"]),
            [{"uuid": str(n), "kind": "get_prop", "position": 0, "config": {"key": "total"}}],
            [],
        ),
    )
    assert created.status_code == 201, created.text
    view = created.json()
    assert view["type_name"] == "Function<Invoice, Numeric>"
    assert view["nodes"][0]["kind"] == "get_prop"
    fn_uuid = view["uuid"]

    assert fn_uuid in [f["uuid"] for f in auth_client.get("/api/functions").json()]
    got = auth_client.get(f"/api/functions/{fn_uuid}")
    assert got.status_code == 200
    assert got.json()["name"] == "total passthrough"

    # bind to Report.amount and read the computed value (total = 100)
    bound = auth_client.put(
        "/api/types/Report/props/amount/function", json={"function_uuid": fn_uuid}
    )
    assert bound.status_code == 200, bound.text
    assert {p["key"]: p for p in bound.json()["props"]}["amount"]["function_uuid"] == fn_uuid
    rep = dsl.create_object(auth_client, "Report", {"name": {"value": "r1"}})
    assert rep["props"]["amount"]["value"] == "100"

    # replace the DAG (total * tax) — edges cross the wire, read updates
    a, b, c = uuid4(), uuid4(), uuid4()
    updated = auth_client.put(
        f"/api/functions/{fn_uuid}",
        json=_function_draft(
            "Invoice",
            "Numeric",
            "taxed",
            str(inv["uuid"]),
            [
                {"uuid": str(a), "kind": "get_prop", "position": 0, "config": {"key": "total"}},
                {"uuid": str(b), "kind": "get_prop", "position": 1, "config": {"key": "tax"}},
                {"uuid": str(c), "kind": "mul", "position": 2, "config": {}},
            ],
            [
                {"from_node_uuid": str(a), "from_port": 0, "to_node_uuid": str(c), "to_port": 0},
                {"from_node_uuid": str(b), "from_port": 0, "to_node_uuid": str(c), "to_port": 1},
            ],
        ),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "taxed"
    reloaded = auth_client.get(f"/api/objects/{rep['uuid']}").json()
    assert reloaded["props"]["amount"]["value"] == "500"

    # delete unbinds and removes the function instance
    assert auth_client.delete(f"/api/functions/{fn_uuid}").status_code == 204
    assert auth_client.get(f"/api/functions/{fn_uuid}").status_code == 404


def test_function_validation_over_http(auth_client: TestClient) -> None:
    from uuid import uuid4

    dsl.create_type(auth_client, "Invoice", {"name": "String", "total": "Numeric"})
    dsl.create_type(auth_client, "Report", {"name": "String", "amount": "Numeric"})

    # internal cycle -> 422
    a, b = uuid4(), uuid4()
    cyclic = auth_client.post(
        "/api/functions",
        json=_function_draft(
            "Invoice",
            "Numeric",
            "cyclic",
            None,
            [
                {"uuid": str(a), "kind": "cast", "position": 0, "config": {"target": "Numeric"}},
                {"uuid": str(b), "kind": "cast", "position": 1, "config": {"target": "Numeric"}},
            ],
            [
                {"from_node_uuid": str(a), "from_port": 0, "to_node_uuid": str(b), "to_port": 0},
                {"from_node_uuid": str(b), "from_port": 0, "to_node_uuid": str(a), "to_port": 0},
            ],
        ),
    )
    assert cyclic.status_code == 422
    assert cyclic.json()["error"]["code"] == "validation"

    # a function-backed prop refuses direct writes (write guard)
    n = uuid4()
    fn = auth_client.post(
        "/api/functions",
        json=_function_draft(
            "Invoice",
            "Numeric",
            "x",
            None,
            [{"uuid": str(n), "kind": "get_prop", "position": 0, "config": {"key": "total"}}],
            [],
        ),
    ).json()
    bound = auth_client.put(
        "/api/types/Report/props/amount/function", json={"function_uuid": fn["uuid"]}
    )
    assert bound.status_code == 200, bound.text
    guarded = auth_client.post(
        "/api/objects",
        json={"type_name": "Report", "props": {"amount": {"value": "1"}}},
    )
    assert guarded.status_code == 422


def test_object_export_markdown(auth_client: TestClient) -> None:
    dsl.create_type(auth_client, "Org", {"name": "String", "city": "String"})
    org = dsl.create_object(
        auth_client,
        "Org",
        {"name": {"value": "Acme"}, "city": {"value": "Barcelona"}},
    )
    org_uuid = str(org["uuid"])

    response = auth_client.get(f"/api/objects/{org_uuid}/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "attachment" in response.headers["content-disposition"]
    assert "Acme.md" in response.headers["content-disposition"]
    assert (
        response.text
        == "# Org: Acme\n\n- **name**: Acme\n- **city**: Barcelona\n"
    )
