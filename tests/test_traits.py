"""Traits (ADR-0013): prop bundles attachable to types, with a color and
the Any<Trait> bound form. Api-level; HTTP shape lives in test_http.py."""
import pytest

from nylium.api import Api, ObjectRef, RefValue, ScalarValue
from nylium.server.errors import ValidationError


def stamped_trait(color: str = "#3a7d5c"):
    return Api.create_trait(
        "Stamped",
        color,
        {"created_note": "String", "priority": "Integer"},
    )


def task_type() -> None:
    _ = Api.create_type("Task", {"name": "String", "title": "String"}, "Tasks")


def test_create_trait_view():
    view = stamped_trait()
    assert view.name == "Stamped"
    assert view.color == "#3a7d5c"
    assert [prop.key for prop in view.props] == ["created_note", "priority"]
    assert view.wire()["attached"] == []


def test_create_trait_duplicate_name():
    _ = stamped_trait()
    with pytest.raises(ValueError, match="already exists"):
        _ = stamped_trait()


def test_create_trait_any_grammar_name_refused():
    with pytest.raises(ValidationError, match="grammar"):
        _ = Api.create_trait("Any<Stamped>", "#3a7d5c", {"note": "String"})


def test_attach_makes_props_effective():
    _ = stamped_trait()
    task_type()
    view = Api.attach_trait("Task", "Stamped")
    assert [t.name for t in view.traits] == ["Stamped"]
    assert [prop.key for prop in view.props] == [
        "name",
        "title",
        "created_note",
        "priority",
    ]
    origin = {prop.key: prop.wire()["trait"] for prop in view.props}
    assert origin["title"] is None
    assert origin["created_note"] == "Stamped"
    colors = {prop.key: prop.wire()["trait_color"] for prop in view.props}
    assert colors["priority"] == "#3a7d5c"


def test_attach_twice_refused():
    _ = stamped_trait()
    task_type()
    _ = Api.attach_trait("Task", "Stamped")
    with pytest.raises(ValueError, match="already attached"):
        _ = Api.attach_trait("Task", "Stamped")


def test_attach_key_collision_refused():
    _ = Api.create_trait("Clashing", "#111111", {"name": "String"})
    task_type()
    with pytest.raises(ValidationError, match="collide"):
        _ = Api.attach_trait("Task", "Clashing")


def test_attach_to_builtin_refused():
    _ = stamped_trait()
    with pytest.raises(ValidationError, match="builtin"):
        _ = Api.attach_trait("String", "Stamped")


def test_detach_removes_props_and_purges_values():
    _ = stamped_trait()
    task_type()
    _ = Api.attach_trait("Task", "Stamped")
    task = Api.create_object(
        "Task", {"name": "t1", "created_note": "hello", "priority": 3}
    )
    view = Api.detach_trait("Task", "Stamped")
    assert [prop.key for prop in view.props] == ["name", "title"]
    reloaded = Api.get_object(task.uuid)
    assert reloaded is not None
    assert set(reloaded.props) == {"name", "title"}


def test_detach_keeps_other_types_values():
    _ = stamped_trait()
    task_type()
    _ = Api.create_type("Bug", {"name": "String"}, "Bugs")
    _ = Api.attach_trait("Task", "Stamped")
    _ = Api.attach_trait("Bug", "Stamped")
    bug = Api.create_object("Bug", {"name": "b1", "priority": 9})
    _ = Api.detach_trait("Task", "Stamped")
    reloaded = Api.get_object(bug.uuid)
    assert reloaded is not None
    assert reloaded.props["priority"] == ScalarValue(value=9)


def test_detach_not_attached():
    _ = stamped_trait()
    task_type()
    with pytest.raises(KeyError, match="not attached"):
        _ = Api.detach_trait("Task", "Stamped")


def test_sync_trait_props_propagates_to_types():
    trait = stamped_trait()
    task_type()
    _ = Api.attach_trait("Task", "Stamped")
    note_uuid = next(p.uuid for p in trait.props if p.key == "created_note")
    synced = Api.sync_trait(
        "Stamped",
        items=[
            (note_uuid, "author_note", "String", None),
            (None, "weight", "Numeric", None),
        ],
    )
    assert [prop.key for prop in synced.props] == ["author_note", "weight"]
    task_view = Api.get_type("Task")
    assert task_view is not None
    assert [prop.key for prop in task_view.props] == [
        "name",
        "title",
        "author_note",
        "weight",
    ]


def test_sync_trait_rename_and_color():
    _ = stamped_trait()
    synced = Api.sync_trait("Stamped", new_name="Labelled", color="#0000ff")
    assert synced.name == "Labelled"
    assert synced.color == "#0000ff"
    assert Api.get_trait("Stamped") is None


def test_sync_trait_formula_refused():
    _ = stamped_trait()
    with pytest.raises(ValidationError, match="no formula"):
        _ = Api.sync_trait("Stamped", items=[(None, "f", "Integer", "1 + 1")])


def test_delete_trait():
    _ = stamped_trait()
    assert Api.delete_trait("Stamped") is True
    assert Api.get_trait("Stamped") is None
    assert Api.delete_trait("Stamped") is False


def test_delete_attached_trait_refused():
    _ = stamped_trait()
    task_type()
    _ = Api.attach_trait("Task", "Stamped")
    with pytest.raises(ValueError, match=r"attached to \['Task'\]"):
        _ = Api.delete_trait("Stamped")


def test_delete_bound_trait_refused():
    _ = stamped_trait()
    task_type()
    task_view = Api.get_type("Task")
    assert task_view is not None
    name_uuid = next(p.uuid for p in task_view.props if p.key == "name")
    _ = Api.sync_props(
        "Task",
        [(name_uuid, "name", "String", None), (None, "related", "Any<Stamped>", None)],
    )
    with pytest.raises(ValueError, match="bound"):
        _ = Api.delete_trait("Stamped")


def test_any_trait_write_validation():
    _ = stamped_trait()
    task_type()
    _ = Api.create_type("Plain", {"name": "String"}, "Plains")
    _ = Api.attach_trait("Task", "Stamped")
    _ = Api.create_type(
        "Link", {"name": "String", "target": "Any<Stamped>"}, "Links"
    )
    task = Api.create_object("Task", {"name": "t1"})
    plain = Api.create_object("Plain", {"name": "p1"})
    ok = Api.create_object("Link", {"name": "l1", "target": task.uuid})
    assert ok.props["target"] == RefValue(ref=ObjectRef(uuid=task.uuid, type_name="Task"))
    # value-type mismatches surface as TypeError (mapped to 422 on HTTP)
    with pytest.raises(TypeError, match="Stamped"):
        _ = Api.create_object("Link", {"name": "l2", "target": plain.uuid})
    with pytest.raises(TypeError, match="Stamped"):
        _ = Api.update_object(ok.uuid, {"target": plain.uuid})


def test_any_trait_wire_name_roundtrip():
    _ = stamped_trait()
    task_type()
    task_view = Api.get_type("Task")
    assert task_view is not None
    name_uuid = next(p.uuid for p in task_view.props if p.key == "name")
    view = Api.sync_props(
        "Task",
        [(name_uuid, "name", "String", None), (None, "related", "Any<Stamped>", None)],
    )
    spec = {prop.key: prop.wire()["value_type"] for prop in view.props}
    assert spec["related"] == "Any<Stamped>"


def test_trait_prop_values_read_write():
    _ = stamped_trait()
    task_type()
    _ = Api.attach_trait("Task", "Stamped")
    task = Api.create_object("Task", {"name": "t1", "priority": 5})
    assert task.props["priority"] == ScalarValue(value=5)
    updated = Api.update_object(task.uuid, {"created_note": "edited"})
    assert updated.props["created_note"] == ScalarValue(value="edited")
    assert updated.props["priority"] == ScalarValue(value=5)


def test_trait_prop_key_collision_with_object_write():
    """Object writes address props by key — a trait prop is just a prop."""
    _ = stamped_trait()
    task_type()
    _ = Api.attach_trait("Task", "Stamped")
    with pytest.raises(KeyError):
        _ = Api.create_object("Task", {"name": "t1", "nonsense": 1})
