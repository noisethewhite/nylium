"""Instances Store: Mapping contract + type index over the instances table (ADR-0010).

``instances`` behaves like ``dict[UUID, TABLE_Instances]`` plus a type index:
``instances[uuid]``, ``instances.get``, ``uuid in instances``,
``instances.by_type`` / ``count_of_type``, and the read helpers
``name_of`` / ``get_type_name`` / ``exists`` / ``owner_of``.
"""
from uuid import UUID, uuid4

import pytest

from nylium.api import Api
from nylium.tables.instances import instances
from nylium.tables.types import types


def _seed_type() -> UUID:
    """create_type seeds the builtins; return the type row uuid of "T"."""
    view = Api.create_type("T", {"name": "String"}, "Ts")
    row = types.by_name(view.name)
    assert row is not None
    return row.uuid


def _seed_instance(type_uuid: UUID) -> UUID:
    uuid = uuid4()
    instances.create(uuid, type_uuid, "instance-1")
    return uuid


def test_getitem_and_contains():
    t = _seed_type()
    u = _seed_instance(t)
    assert instances[u].name == "instance-1"
    assert instances[u].type_uuid == t
    assert u in instances
    with pytest.raises(KeyError):
        _ = instances[uuid4()]


def test_by_type_and_count():
    t = _seed_type()
    u1 = _seed_instance(t)
    u2 = _seed_instance(t)
    assert set(instances.by_type(t)) >= {u1, u2}
    assert instances.count_of_type(t) >= 2


def test_read_helpers():
    t = _seed_type()
    u = _seed_instance(t)
    assert instances.name_of(u) == "instance-1"
    assert instances.get_type_name(u) == "T"
    assert instances.exists(u)
    assert not instances.exists(uuid4())
    assert instances.owner_of(u) is None  # standalone, not embedded
