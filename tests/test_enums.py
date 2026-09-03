"""String enums: kind='enum' types, option CRUD with propagation,
membership validation on write. Api-level; HTTP shape lives in
test_http.py."""
import pytest

from nylium.api import Api, ArrayValue, ScalarValue, TypeView
from nylium.server.errors import ValidationError


def ticket_type() -> TypeView:
    return Api.create_type(
        "Ticket",
        {"name": "String", "status": "Status", "tags": "Array<Status>"},
        "Tickets",
    )


def status_enum() -> TypeView:
    return Api.create_enum("Status", ["open", "closed"])


def test_create_enum_view():
    view = status_enum()
    assert view.kind == "enum"
    assert [option.value for option in view.enum_options] == ["open", "closed"]
    assert view.props == []


def test_enum_membership_validation():
    _ = status_enum()
    _ = ticket_type()
    created = Api.create_object("Ticket", {"name": "t1", "status": "open"})
    assert created.props["status"] == ScalarValue(value="open")
    with pytest.raises(ValidationError):
        Api.create_object("Ticket", {"name": "t2", "status": "bogus"})
    with pytest.raises(ValidationError):
        Api.update_object(created.uuid, {"status": "bogus"})


def test_enum_unset_and_empty_name():
    _ = status_enum()
    _ = ticket_type()
    created = Api.create_object("Ticket", {"status": "open"})
    assert created.props["name"] == ScalarValue(value=None)
    assert created.props["status"] == ScalarValue(value="open")


def test_enum_array_prop():
    _ = status_enum()
    _ = ticket_type()
    created = Api.create_object("Ticket", {"name": "t1", "tags": ["open", "closed"]})
    assert created.props["tags"] == ArrayValue(
        items=[ScalarValue(value="open"), ScalarValue(value="closed")]
    )
    with pytest.raises(ValidationError):
        Api.update_object(created.uuid, {"tags": ["open", "bogus"]})


def _option_uuids(view: TypeView) -> dict[str, object]:
    return {option.value: option.uuid for option in view.enum_options}


def test_sync_options_rename_propagates():
    view = status_enum()
    _ = ticket_type()
    ticket = Api.create_object("Ticket", {"name": "t1", "status": "open"})
    uuids = _option_uuids(view)
    synced = Api.sync_enum_options(
        "Status", [(uuids["open"], "in progress"), (None, "archived")]  # type: ignore[list-item]
    )
    assert [option.value for option in synced.enum_options] == ["in progress", "archived"]
    reloaded = Api.get_object(ticket.uuid)
    assert reloaded is not None
    assert reloaded.props["status"] == ScalarValue(value="in progress")


def test_sync_options_delete_in_use_refused():
    view = status_enum()
    _ = ticket_type()
    _ = Api.create_object("Ticket", {"name": "t1", "status": "open"})
    uuids = _option_uuids(view)
    with pytest.raises(ValueError):
        Api.sync_enum_options("Status", [(uuids["closed"], "closed")])  # type: ignore[list-item]


def test_sync_options_delete_unused_ok():
    view = status_enum()
    _ = ticket_type()
    uuids = _option_uuids(view)
    synced = Api.sync_enum_options("Status", [(uuids["open"], "open")])  # type: ignore[list-item]
    assert [option.value for option in synced.enum_options] == ["open"]


def test_sync_options_guards():
    view = status_enum()
    uuids = _option_uuids(view)
    with pytest.raises(ValidationError):
        Api.sync_enum_options("Status", [(uuids["open"], ""), (None, "closed")])  # type: ignore[list-item]
    with pytest.raises(ValidationError):
        Api.sync_enum_options("Status", [(uuids["open"], "dup"), (None, "dup")])  # type: ignore[list-item]
    with pytest.raises(KeyError):
        Api.sync_enum_options("NoSuchEnum", [])
    _ = Api.create_type("Plain", {"name": "String"}, "Plains")
    with pytest.raises(ValidationError):
        Api.sync_enum_options("Plain", [])


def test_enum_rename_and_identity():
    _ = status_enum()
    renamed = Api.rename_type("Status", "TicketStatus")
    assert renamed.name == "TicketStatus" and renamed.kind == "enum"
    assert [option.value for option in renamed.enum_options] == ["open", "closed"]
    assert Api.get_type("Status") is None
