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
    view = Api.create_type("Note", {"body": "String"}, "Notes")
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
