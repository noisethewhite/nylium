"""Embedded (composition) instances: types whose instances exist only as
a prop value of an owner object (ADR-0004). Lazy create on first write,
generated names, cascade delete, guards against standalone use.
Api-level; HTTP shape lives in test_http.py."""
from uuid import UUID

import pytest

from nylium.api import Api, EmbeddedValue, ScalarValue, TypeView
from nylium.server.errors import ValidationError


def contact_details_type() -> TypeView:
    return Api.create_type(
        "ContactDetails",
        {"name": "String", "email": "String", "phone": "String"},
        "ContactDetails",
        embedded=True,
    )


def person_type() -> TypeView:
    _ = contact_details_type()
    return Api.create_type(
        "Person",
        {"name": "String", "contact": "ContactDetails"},
        "People",
    )


def test_create_embedded_type_view():
    view = contact_details_type()
    assert view.embedded is True
    assert view.kind == "object"
    assert [prop.key for prop in view.props] == ["name", "email", "phone"]
    # a regular type is not embedded
    assert person_type().embedded is False


def test_standalone_create_refused():
    _ = contact_details_type()
    with pytest.raises(ValidationError):
        Api.create_object("ContactDetails", {"name": "x", "email": "a@b.c"})


def test_lazy_create_and_generated_name():
    _ = person_type()
    person = Api.create_object("Person", {"name": "Vasya"})
    # untouched embedded prop: no child yet
    assert person.props["contact"] == EmbeddedValue(
        uuid=None, type_name="ContactDetails", props={}
    )
    # first fill creates the child lazily, with a generated name
    person = Api.update_object(
        person.uuid, {"contact": {"email": "v@x.com", "phone": "+1"}}
    )
    contact = person.props["contact"]
    assert isinstance(contact, EmbeddedValue)
    assert contact.uuid is not None
    assert contact.props["email"] == ScalarValue(value="v@x.com")
    assert contact.props["name"] == ScalarValue(value="Vasya → contact")
    # the child is readable by uuid, but never listed standalone
    assert Api.get_object(contact.uuid) is not None
    assert Api.list_objects("ContactDetails") == []


def test_name_generated_when_draft_precedes_parent_name():
    _ = person_type()
    # dict order puts the embedded draft before the name prop: the name
    # write must still heal the child's generated name afterwards
    person = Api.create_object(
        "Person", {"contact": {"email": "v@x.com"}, "name": "Vasya"}
    )
    contact = person.props["contact"]
    assert isinstance(contact, EmbeddedValue)
    assert contact.props["name"] == ScalarValue(value="Vasya → contact")


def test_name_regenerated_on_parent_rename():
    _ = person_type()
    person = Api.create_object(
        "Person", {"name": "Vasya", "contact": {"email": "v@x.com"}}
    )
    person = Api.update_object(person.uuid, {"name": "Petya"})
    contact = person.props["contact"]
    assert isinstance(contact, EmbeddedValue)
    assert contact.props["name"] == ScalarValue(value="Petya → contact")


def test_update_embedded_keeps_child_identity():
    _ = person_type()
    person = Api.create_object(
        "Person", {"name": "Vasya", "contact": {"email": "v@x.com"}}
    )
    before = person.props["contact"]
    assert isinstance(before, EmbeddedValue)
    person = Api.update_object(person.uuid, {"contact": {"phone": "+2"}})
    after = person.props["contact"]
    assert isinstance(after, EmbeddedValue)
    assert after.uuid == before.uuid
    assert after.props["email"] == ScalarValue(value="v@x.com")
    assert after.props["phone"] == ScalarValue(value="+2")


def test_clear_prop_deletes_child():
    _ = person_type()
    person = Api.create_object(
        "Person", {"name": "Vasya", "contact": {"email": "v@x.com"}}
    )
    contact = person.props["contact"]
    assert isinstance(contact, EmbeddedValue) and contact.uuid is not None
    person = Api.update_object(person.uuid, {"contact": None})
    assert person.props["contact"] == EmbeddedValue(
        uuid=None, type_name="ContactDetails", props={}
    )
    assert Api.get_object(contact.uuid) is None


def test_parent_delete_cascades():
    _ = person_type()
    person = Api.create_object(
        "Person", {"name": "Vasya", "contact": {"email": "v@x.com"}}
    )
    contact = person.props["contact"]
    assert isinstance(contact, EmbeddedValue) and contact.uuid is not None
    assert Api.delete_object(person.uuid)
    assert Api.get_object(contact.uuid) is None


def test_direct_write_and_delete_of_child_refused():
    _ = person_type()
    person = Api.create_object(
        "Person", {"name": "Vasya", "contact": {"email": "v@x.com"}}
    )
    contact = person.props["contact"]
    assert isinstance(contact, EmbeddedValue) and contact.uuid is not None
    with pytest.raises(ValidationError):
        Api.update_object(contact.uuid, {"email": "other@x.com"})
    with pytest.raises(ValidationError):
        Api.delete_object(contact.uuid)


def test_link_to_existing_refused():
    _ = person_type()
    person = Api.create_object(
        "Person", {"name": "Vasya", "contact": {"email": "v@x.com"}}
    )
    contact = person.props["contact"]
    assert isinstance(contact, EmbeddedValue) and contact.uuid is not None
    # an embedded prop takes an inline draft, never a link (ADR-0004)
    with pytest.raises(TypeError):
        Api.create_object(
            "Person", {"name": "Petya", "contact": UUID(str(contact.uuid))}
        )


def test_array_of_embedded_refused():
    _ = contact_details_type()
    with pytest.raises(ValidationError):
        Api.create_type(
            "Team", {"name": "String", "members": "Array<ContactDetails>"}, "Teams"
        )


def test_reserved_separator():
    with pytest.raises(ValidationError):
        Api.create_type("A → B", {"name": "String"}, "ABs")
    with pytest.raises(ValidationError):
        Api.create_type("Bad", {"name": "String", "a → b": "String"}, "Bads")
    with pytest.raises(ValidationError):
        Api.create_enum("E → x", ["a"])
    with pytest.raises(ValidationError):
        Api.create_unit("U → x", "kg")
    _ = Api.create_type("Plain", {"name": "String"}, "Plains")
    with pytest.raises(ValidationError):
        Api.rename_type("Plain", "Plain → x")
    with pytest.raises(ValidationError):
        Api.create_object("Plain", {"name": "a → b"})


def test_sync_props_delete_destroys_children():
    view = person_type()
    person = Api.create_object(
        "Person", {"name": "Vasya", "contact": {"email": "v@x.com"}}
    )
    contact = person.props["contact"]
    assert isinstance(contact, EmbeddedValue) and contact.uuid is not None
    name_prop = next(prop for prop in view.props if prop.key == "name")
    # drop the contact prop from the schema entirely
    synced = Api.sync_props("Person", [(name_prop.uuid, "name", "String")])
    assert [prop.key for prop in synced.props] == ["name"]
    assert Api.get_object(contact.uuid) is None


def test_sync_props_rename_regenerates_names():
    view = person_type()
    person = Api.create_object(
        "Person", {"name": "Vasya", "contact": {"email": "v@x.com"}}
    )
    contact = person.props["contact"]
    assert isinstance(contact, EmbeddedValue) and contact.uuid is not None
    items = [(prop.uuid, prop.key, prop.value_type) for prop in view.props]
    items = [
        (uuid, "details" if key == "contact" else key, vt) for uuid, key, vt in items
    ]
    _ = Api.sync_props("Person", items)
    reloaded = Api.get_object(person.uuid)
    assert reloaded is not None
    details = reloaded.props["details"]
    assert isinstance(details, EmbeddedValue)
    assert details.uuid == contact.uuid
    assert details.props["name"] == ScalarValue(value="Vasya → details")


def test_nested_embedded_names():
    _ = Api.create_type(
        "Address", {"name": "String", "city": "String"}, "Addresses", embedded=True
    )
    _ = Api.create_type(
        "ContactDetails",
        {"name": "String", "address": "Address"},
        "ContactDetails",
        embedded=True,
    )
    _ = Api.create_type(
        "Person", {"name": "String", "contact": "ContactDetails"}, "People"
    )
    person = Api.create_object(
        "Person",
        {"name": "Vasya", "contact": {"address": {"city": "Barcelona"}}},
    )
    contact = person.props["contact"]
    assert isinstance(contact, EmbeddedValue)
    address = contact.props["address"]
    assert isinstance(address, EmbeddedValue)
    assert address.props["city"] == ScalarValue(value="Barcelona")
    assert address.props["name"] == ScalarValue(value="Vasya → contact → address")
    # deleting the parent cascades through the whole tree
    assert isinstance(contact.uuid, UUID) and isinstance(address.uuid, UUID)
    assert Api.delete_object(person.uuid)
    assert Api.get_object(contact.uuid) is None
    assert Api.get_object(address.uuid) is None
