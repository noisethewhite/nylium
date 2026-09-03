"""Api facade: CRUD over types and objects, view-shaped returns.
Classes live inside tests — see test_objects.py for why."""
import pytest

from nylium.api import (
    Api,
    ArrayValue,
    ObjectRef,
    ObjectView,
    RefValue,
    ScalarValue,
    TypeView,
)
from nylium.objects import WInteger, WObject, WString
from nylium.server.errors import ValidationError


def person_class() -> type[WObject]:
    class Person(WObject):
        name: WString
        age: WInteger
        friend: "Person"
        tags: list[WString]

    return Person


def test_type_listing():
    _ = person_class()
    views = {view.name: view for view in Api.list_types()}
    assert "Person" in views
    person = views["Person"]
    assert isinstance(person, TypeView)
    props = {prop.key: prop.value_type for prop in person.props}
    assert props["name"] == "String"
    assert props["tags"] == "Array<String>"


def test_get_missing_type():
    assert Api.get_type("NoSuchType") is None


def test_object_crud_round_trip():
    _ = person_class()
    created = Api.create_object("Person", {"name": "Max", "age": 26})
    assert isinstance(created, ObjectView)
    assert created.type_name == "Person"
    assert created.props["name"] == ScalarValue(value="Max")
    assert created.props["tags"] == ArrayValue(items=None)  # set vs unset

    fetched = Api.get_object(created.uuid)
    assert fetched is not None and fetched.props["age"] == ScalarValue(value=26)

    updated = Api.update_object(created.uuid, {"age": 27})
    assert updated.props["age"] == ScalarValue(value=27)

    listing = Api.list_objects("Person")
    assert [view.uuid for view in listing] == [created.uuid]

    assert Api.delete_object(created.uuid) is True
    assert Api.get_object(created.uuid) is None
    assert Api.delete_object(created.uuid) is False


def test_links_and_arrays_render_as_views():
    _ = person_class()
    oleg = Api.create_object("Person", {"name": "Oleg", "age": 30})
    maxim = Api.create_object("Person", {"name": "Max", "age": 26})
    # links come in as UUID or ObjectRef — that's all an API caller has
    Api.update_object(oleg.uuid, {"friend": ObjectRef(uuid=maxim.uuid, type_name="Person")})
    Api.update_object(oleg.uuid, {"friend": maxim.uuid, "tags": ["admin", "owner"]})

    view = Api.get_object(oleg.uuid)
    assert view is not None
    friend = view.props["friend"]
    assert isinstance(friend, RefValue) and friend.ref is not None
    assert friend.ref.uuid == maxim.uuid and friend.ref.type_name == "Person"
    assert view.props["tags"] == ArrayValue(
        items=[ScalarValue(value="admin"), ScalarValue(value="owner")]
    )


def test_db_only_type_created_through_api():
    view = Api.create_type("Note", {"name": "String", "body": "String"}, "Notes")
    assert view.name == "Note"
    assert view.plural_name == "Notes"

    note = Api.create_object("Note", {"body": "hello"})
    assert note.props["body"] == ScalarValue(value="hello")

    with pytest.raises(TypeError):
        Api.create_object("Note", {"body": 42})


def test_create_object_rejects_bad_values():
    _ = person_class()
    with pytest.raises(TypeError):
        Api.create_object("Person", {"age": True})


def test_delete_type_refuses_with_instances():
    _ = person_class()
    Api.create_object("Person", {"name": "Max"})
    with pytest.raises(ValueError):
        Api.delete_type("Person")


def test_delete_type_when_empty():
    _ = person_class()
    assert Api.delete_type("Person") is True
    assert Api.get_type("Person") is None
    assert Api.delete_type("Person") is False


def test_reorder_props_roundtrip():
    _ = person_class()
    view = Api.reorder_props("Person", ["name", "tags", "age", "friend"])
    assert [prop.key for prop in view.props] == ["name", "tags", "age", "friend"]
    reloaded = Api.get_type("Person")
    assert reloaded is not None
    assert [prop.key for prop in reloaded.props] == ["name", "tags", "age", "friend"]


def test_reorder_props_keeps_name_first():
    _ = person_class()
    with pytest.raises(ValidationError):
        Api.reorder_props("Person", ["age", "tags", "name", "friend"])


def test_create_type_requires_name_prop_first():
    with pytest.raises(ValidationError):
        Api.create_type("Note", {"body": "String"})
    with pytest.raises(ValidationError):
        Api.create_type("Note", {"name": "Integer"})
    with pytest.raises(ValidationError):
        Api.create_type("Note", {})


def test_reorder_props_rejects_foreign_keys():
    _ = person_class()
    with pytest.raises(ValueError):
        Api.reorder_props("Person", ["name", "age"])
    with pytest.raises(KeyError):
        Api.reorder_props("NoSuchType", ["name"])


def note_type():
    return Api.create_type(
        "Note",
        {"name": "String", "body": "String", "priority": "Integer"},
        "Notes",
    )


def draft_items(view, drop=(), rename=None, retype=None, add=()):
    """Build a sync_props draft from a view: drop/rename/retype by key,
    then append (key, value type) additions."""
    rename = rename or {}
    retype = retype or {}
    items = [
        (prop.uuid, rename.get(prop.key, prop.key), retype.get(prop.key, prop.value_type))
        for prop in view.props
        if prop.key not in drop
    ]
    return items + [(None, key, value_type) for key, value_type in add]


def test_sync_props_add_and_delete():
    view = note_type()
    note = Api.create_object("Note", {"name": "n1", "body": "hello"})
    synced = Api.sync_props(
        "Note", draft_items(view, drop=("body",), add=[("mood", "String")])
    )
    assert [prop.key for prop in synced.props] == ["name", "priority", "mood"]
    reloaded = Api.get_object(note.uuid)
    assert reloaded is not None
    assert "body" not in reloaded.props
    assert reloaded.props["mood"] == ScalarValue(value=None)


def test_sync_props_rename_keeps_values():
    view = note_type()
    note = Api.create_object("Note", {"name": "n1", "body": "hello"})
    synced = Api.sync_props("Note", draft_items(view, rename={"body": "text"}))
    assert [prop.key for prop in synced.props] == ["name", "text", "priority"]
    reloaded = Api.get_object(note.uuid)
    assert reloaded is not None
    assert reloaded.props["text"] == ScalarValue(value="hello")


def test_sync_props_retype_purges_values():
    view = note_type()
    note = Api.create_object("Note", {"name": "n1", "priority": 5})
    synced = Api.sync_props("Note", draft_items(view, retype={"priority": "String"}))
    assert {p.key: p.value_type for p in synced.props}["priority"] == "String"
    reloaded = Api.get_object(note.uuid)
    assert reloaded is not None
    assert reloaded.props["priority"] == ScalarValue(value=None)


def test_sync_props_keeps_name_pinned():
    view = note_type()
    with pytest.raises(ValidationError):
        Api.sync_props("Note", draft_items(view, drop=("name",)))
    with pytest.raises(ValidationError):
        Api.sync_props("Note", draft_items(view, rename={"name": "title"}))
    with pytest.raises(ValidationError):
        Api.sync_props("Note", draft_items(view, retype={"name": "Integer"}))


def test_sync_props_rejects_bad_drafts():
    view = note_type()
    body = next(prop for prop in view.props if prop.key == "body")
    with pytest.raises(ValidationError):
        Api.sync_props("Note", draft_items(view, add=[("body", "String")]))
    with pytest.raises(ValidationError):
        Api.sync_props("Note", draft_items(view, add=[("", "String")]))
    forged = [(body.uuid, "body", "String")]
    with pytest.raises(ValidationError):
        Api.sync_props("Note", forged + draft_items(view, drop=("body",)))
    with pytest.raises(KeyError):
        Api.sync_props("NoSuchType", forged)


def test_rename_type_roundtrip():
    _ = note_type()
    note = Api.create_object("Note", {"name": "n1"})
    renamed = Api.rename_type("Note", "Memo", "Memos")
    assert renamed.name == "Memo" and renamed.plural_name == "Memos"
    reloaded = Api.get_object(note.uuid)
    assert reloaded is not None and reloaded.type_name == "Memo"
    assert Api.get_type("Note") is None
    assert Api.get_type("Memo") is not None


def test_rename_type_guards():
    _ = note_type()
    with pytest.raises(ValueError):
        Api.rename_type("Note", "String")  # collision with a builtin
    with pytest.raises(ValidationError):
        Api.rename_type("Note", "")  # empty name
    with pytest.raises(ValidationError):
        Api.rename_type("String", "Text")  # builtins are immutable
    with pytest.raises(KeyError):
        Api.rename_type("NoSuchType", "Memo")
