"""Embedded (composition) instances: types whose instances exist only as
a prop value of an owner object (ADR-0004). Lazy create on first write,
generated names, cascade delete, guards against standalone use.
Api-level; HTTP shape lives in test_http.py."""
from decimal import Decimal
from uuid import UUID

import pytest

from nylium.api import Api, ArrayValue, EmbeddedValue, ScalarValue
from nylium.objects.navigation import effective_props, prop_value_type_name
from nylium.rows.objects.type import Type
from nylium.server.errors import ValidationError


def contact_details_type() -> Type:
    return Api.create_type(
        "ContactDetails",
        {"name": "String", "email": "String", "phone": "String"},
        "ContactDetails",
        embedded=True,
    )


def person_type() -> Type:
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
    assert [prop.key for prop in effective_props(view.uuid)] == ["name", "email", "phone"]
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


def team_type() -> Type:
    _ = contact_details_type()
    return Api.create_type(
        "Team", {"name": "String", "members": "Array<ContactDetails>"}, "Teams"
    )


def test_array_of_embedded_round_trip():
    _ = team_type()
    team = Api.create_object(
        "Team",
        {
            "name": "A-Team",
            "members": [{"email": "a@x.com"}, {"email": "b@x.com"}],
        },
    )
    members = team.props["members"]
    assert isinstance(members, ArrayValue)
    assert members.items is not None and len(members.items) == 2
    first, second = members.items
    assert isinstance(first, EmbeddedValue) and isinstance(second, EmbeddedValue)
    assert first.props["email"] == ScalarValue(value="a@x.com")
    assert second.props["email"] == ScalarValue(value="b@x.com")
    # generated names carry the array prop key and the 1-based position
    assert first.props["name"] == ScalarValue(value="A-Team → members #1")
    assert second.props["name"] == ScalarValue(value="A-Team → members #2")
    # elements are readable by uuid but never listed standalone
    first_uuid = first.uuid
    assert isinstance(first_uuid, UUID) and Api.get_object(first_uuid) is not None
    assert Api.list_objects("ContactDetails") == []


def test_array_of_embedded_rewrite_deletes_old_elements():
    _ = team_type()
    team = Api.create_object(
        "Team",
        {"name": "A-Team", "members": [{"email": "a@x.com"}, {"email": "b@x.com"}]},
    )
    members = team.props["members"]
    assert isinstance(members, ArrayValue) and members.items is not None
    old_uuids = [
        item.uuid
        for item in members.items
        if isinstance(item, EmbeddedValue) and item.uuid is not None
    ]
    assert len(old_uuids) == 2
    team = Api.update_object(team.uuid, {"members": [{"email": "c@x.com"}]})
    members = team.props["members"]
    assert isinstance(members, ArrayValue) and members.items is not None
    assert len(members.items) == 1
    for uuid in old_uuids:
        assert Api.get_object(uuid) is None


def test_array_of_embedded_cascade_delete():
    _ = team_type()
    team = Api.create_object(
        "Team",
        {"name": "A-Team", "members": [{"email": "a@x.com"}, {"email": "b@x.com"}]},
    )
    members = team.props["members"]
    assert isinstance(members, ArrayValue) and members.items is not None
    member_uuids = [
        item.uuid
        for item in members.items
        if isinstance(item, EmbeddedValue) and item.uuid is not None
    ]
    assert len(member_uuids) == 2
    assert Api.delete_object(team.uuid)
    for uuid in member_uuids:
        assert Api.get_object(uuid) is None


def test_array_of_embedded_empty_and_clear():
    _ = team_type()
    team = Api.create_object(
        "Team",
        {"name": "A-Team", "members": [{"email": "a@x.com"}]},
    )
    members = team.props["members"]
    assert isinstance(members, ArrayValue) and members.items is not None
    member = members.items[0]
    assert isinstance(member, EmbeddedValue)
    member_uuid = member.uuid
    assert member_uuid is not None
    # `[]` empties the array, deleting the composed children
    team = Api.update_object(team.uuid, {"members": []})
    members = team.props["members"]
    assert isinstance(members, ArrayValue) and members.items == []
    assert Api.get_object(member_uuid) is None
    # `None` unsets the prop entirely, also deleting composed children
    team = Api.update_object(team.uuid, {"members": [{"email": "b@x.com"}]})
    members = team.props["members"]
    assert isinstance(members, ArrayValue) and members.items is not None
    second = members.items[0]
    assert isinstance(second, EmbeddedValue) and second.uuid is not None
    second_uuid = second.uuid
    team = Api.update_object(team.uuid, {"members": None})
    assert team.props["members"] == ArrayValue(items=None)
    assert Api.get_object(second_uuid) is None


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
    name_prop = next(prop for prop in effective_props(view.uuid) if prop.key == "name")
    # drop the contact prop from the schema entirely
    synced = Api.sync_props("Person", [(name_prop.uuid, "name", "String", None)])
    assert [prop.key for prop in effective_props(synced.uuid)] == ["name"]
    assert Api.get_object(contact.uuid) is None


def test_sync_props_rename_regenerates_names():
    view = person_type()
    person = Api.create_object(
        "Person", {"name": "Vasya", "contact": {"email": "v@x.com"}}
    )
    contact = person.props["contact"]
    assert isinstance(contact, EmbeddedValue) and contact.uuid is not None
    items = [
        (prop.uuid, prop.key, prop_value_type_name(prop), prop.formula)
        for prop in effective_props(view.uuid)
    ]
    items = [
        (uuid, "details" if key == "contact" else key, vt, formula)
        for uuid, key, vt, formula in items
    ]
    _ = Api.sync_props("Person", items)
    reloaded = Api.get_object(person.uuid)
    assert reloaded is not None
    details = reloaded.props["details"]
    assert isinstance(details, EmbeddedValue)
    assert details.uuid == contact.uuid
    assert details.props["name"] == ScalarValue(value="Vasya → details")


def test_array_of_embedded_parent_rename_regenerates_names():
    _ = team_type()
    team = Api.create_object(
        "Team",
        {"name": "A-Team", "members": [{"email": "a@x.com"}, {"email": "b@x.com"}]},
    )
    members = team.props["members"]
    assert isinstance(members, ArrayValue) and members.items is not None
    first, second = members.items
    assert isinstance(first, EmbeddedValue) and isinstance(second, EmbeddedValue)
    assert first.props["name"] == ScalarValue(value="A-Team → members #1")
    team = Api.update_object(team.uuid, {"name": "B-Team"})
    members = team.props["members"]
    assert isinstance(members, ArrayValue) and members.items is not None
    first, second = members.items
    assert isinstance(first, EmbeddedValue) and isinstance(second, EmbeddedValue)
    assert first.props["name"] == ScalarValue(value="B-Team → members #1")
    assert second.props["name"] == ScalarValue(value="B-Team → members #2")


def test_sync_props_delete_destroys_array_children():
    view = team_type()
    team = Api.create_object(
        "Team",
        {"name": "A-Team", "members": [{"email": "a@x.com"}, {"email": "b@x.com"}]},
    )
    members = team.props["members"]
    assert isinstance(members, ArrayValue) and members.items is not None
    member_uuids = [
        item.uuid
        for item in members.items
        if isinstance(item, EmbeddedValue) and item.uuid is not None
    ]
    assert len(member_uuids) == 2
    name_prop = next(prop for prop in effective_props(view.uuid) if prop.key == "name")
    # drop the members prop from the schema entirely
    synced = Api.sync_props("Team", [(name_prop.uuid, "name", "String", None)])
    assert [prop.key for prop in effective_props(synced.uuid)] == ["name"]
    for uuid in member_uuids:
        assert Api.get_object(uuid) is None


def test_sync_props_rename_regenerates_array_names():
    view = team_type()
    team = Api.create_object(
        "Team",
        {"name": "A-Team", "members": [{"email": "a@x.com"}, {"email": "b@x.com"}]},
    )
    members = team.props["members"]
    assert isinstance(members, ArrayValue) and members.items is not None
    member_uuids = [
        item.uuid
        for item in members.items
        if isinstance(item, EmbeddedValue) and item.uuid is not None
    ]
    assert len(member_uuids) == 2
    items = [
        (prop.uuid, prop.key, prop_value_type_name(prop), prop.formula)
        for prop in effective_props(view.uuid)
    ]
    items = [
        (uuid, "crew" if key == "members" else key, vt, formula)
        for uuid, key, vt, formula in items
    ]
    _ = Api.sync_props("Team", items)
    reloaded = Api.get_object(team.uuid)
    assert reloaded is not None
    crew = reloaded.props["crew"]
    assert isinstance(crew, ArrayValue) and crew.items is not None
    assert [
        item.uuid
        for item in crew.items
        if isinstance(item, EmbeddedValue) and item.uuid is not None
    ] == member_uuids
    first, second = crew.items
    assert isinstance(first, EmbeddedValue) and isinstance(second, EmbeddedValue)
    assert first.props["name"] == ScalarValue(value="A-Team → crew #1")
    assert second.props["name"] == ScalarValue(value="A-Team → crew #2")


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


def test_embedded_type_may_omit_name():
    # ADR-0027: embedded composition types are not required to carry a
    # `name` prop — e.g. a receipt line identifies itself by its product
    # reference, not a generated title.
    view = Api.create_type("Item", {"sku": "String", "qty": "Numeric"}, "Items", embedded=True)
    assert view.embedded is True
    assert [prop.key for prop in effective_props(view.uuid)] == ["sku", "qty"]


def test_name_less_embedded_array():
    _ = Api.create_type("Item", {"sku": "String", "qty": "Numeric"}, "Items", embedded=True)
    _ = Api.create_type("Order", {"name": "String", "lines": "Array<Item>"}, "Orders")
    order = Api.create_object(
        "Order", {"name": "N1", "lines": [{"sku": "A", "qty": Decimal("2")}]}
    )
    lines = order.props["lines"]
    assert isinstance(lines, ArrayValue) and lines.items is not None
    item = lines.items[0]
    assert isinstance(item, EmbeddedValue)
    # no generated `name` prop — name-less embedded types keep their registry
    # name instead (display falls back to it in the UI)
    assert "name" not in item.props
    assert item.props["sku"] == ScalarValue(value="A")
    assert item.props["qty"] == ScalarValue(value=Decimal("2"))
    # readable by uuid, never listed standalone
    assert isinstance(item.uuid, UUID) and Api.get_object(item.uuid) is not None
    assert Api.list_objects("Item") == []
