"""String enums: kind='enum' types, option CRUD with propagation,
membership validation on write. Api-level; HTTP shape lives in
test_http.py."""
from uuid import UUID

import pytest

from nylium.api import Api, ArrayValueView, ScalarValueView
from nylium.data.rows import Type
from nylium.server.ValidationError import ValidationError
from nylium.uuid import TypeUUID


def ticket_type() -> Type:
    return Api.create_type(
        "Ticket",
        {"name": "String", "status": "Status", "tags": "Array<Status>"},
        "Tickets",
    )


def status_enum() -> Type:
    return Api.create_enum("Status", ["open", "closed"])


def test_create_enum_view():
    view = status_enum()
    assert view.kind == "enum"
    assert [option.value for option in TypeUUID.of(view.uuid).enum_options()] == ["open", "closed"]
    assert TypeUUID.of(view.uuid).effective_props() == []


def test_enum_membership_validation():
    _ = status_enum()
    _ = ticket_type()
    created = Api.create_object("Ticket", {"name": "t1", "status": "open"})
    assert created.props["status"] == ScalarValueView(value="open")
    with pytest.raises(ValidationError):
        Api.create_object("Ticket", {"name": "t2", "status": "bogus"})
    with pytest.raises(ValidationError):
        Api.update_object(created.uuid, {"status": "bogus"})


def test_enum_unset_and_empty_name():
    _ = status_enum()
    _ = ticket_type()
    created = Api.create_object("Ticket", {"status": "open"})
    assert created.props["name"] == ScalarValueView(value=None)
    assert created.props["status"] == ScalarValueView(value="open")


def test_enum_array_prop():
    _ = status_enum()
    _ = ticket_type()
    created = Api.create_object("Ticket", {"name": "t1", "tags": ["open", "closed"]})
    assert created.props["tags"] == ArrayValueView(
        items=[ScalarValueView(value="open"), ScalarValueView(value="closed")]
    )
    with pytest.raises(ValidationError):
        Api.update_object(created.uuid, {"tags": ["open", "bogus"]})


def _option_uuids(view: Type) -> dict[str, UUID]:
    return {option.value: option.uuid for option in TypeUUID.of(view.uuid).enum_options()}


def test_sync_options_rename_propagates():
    view = status_enum()
    _ = ticket_type()
    ticket = Api.create_object("Ticket", {"name": "t1", "status": "open"})
    uuids = _option_uuids(view)
    # list invariance: mixed (uuid, value) / (None, value) tuples need
    # the declared element type, not the inferred join
    draft: list[tuple[UUID | None, str]] = [(uuids["open"], "in progress"), (None, "archived")]
    synced = Api.sync_enum_options("Status", draft)
    assert [option.value for option in TypeUUID.of(synced.uuid).enum_options()] == ["in progress", "archived"]
    reloaded = Api.get_object(ticket.uuid)
    assert reloaded is not None
    assert reloaded.props["status"] == ScalarValueView(value="in progress")


def test_sync_options_delete_in_use_refused():
    view = status_enum()
    _ = ticket_type()
    _ = Api.create_object("Ticket", {"name": "t1", "status": "open"})
    uuids = _option_uuids(view)
    draft: list[tuple[UUID | None, str]] = [(uuids["closed"], "closed")]
    with pytest.raises(ValueError):
        Api.sync_enum_options("Status", draft)


def test_sync_options_delete_unused_ok():
    view = status_enum()
    _ = ticket_type()
    uuids = _option_uuids(view)
    draft: list[tuple[UUID | None, str]] = [(uuids["open"], "open")]
    synced = Api.sync_enum_options("Status", draft)
    assert [option.value for option in TypeUUID.of(synced.uuid).enum_options()] == ["open"]


def test_sync_options_guards():
    view = status_enum()
    uuids = _option_uuids(view)
    with pytest.raises(ValidationError):
        bad: list[tuple[UUID | None, str]] = [(uuids["open"], ""), (None, "closed")]
        Api.sync_enum_options("Status", bad)
    with pytest.raises(ValidationError):
        dup: list[tuple[UUID | None, str]] = [(uuids["open"], "dup"), (None, "dup")]
        Api.sync_enum_options("Status", dup)
    with pytest.raises(KeyError):
        Api.sync_enum_options("NoSuchEnum", [])
    _ = Api.create_type("Plain", {"name": "String"}, "Plains")
    with pytest.raises(ValidationError):
        Api.sync_enum_options("Plain", [])


def test_enum_rename_and_identity():
    _ = status_enum()
    renamed = Api.rename_type("Status", "TicketStatus")
    assert renamed.name == "TicketStatus" and renamed.kind == "enum"
    assert [option.value for option in TypeUUID.of(renamed.uuid).enum_options()] == ["open", "closed"]
    assert Api.get_type("Status") is None
