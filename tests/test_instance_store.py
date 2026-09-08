"""Instances Store: Mapping contract over the instances table (ADR-0010).

``instances`` behaves like ``Mapping[UUID, Instance]``: ``instances[uuid]``,
``instances.get``, ``uuid in instances``. Reverse lookups go through
``instances.where(type_uuid=t)``; joined fields hang on the row
(``Instance.type_name``).
"""
from uuid import UUID, uuid4

import pytest

from nylium.api import Api
from nylium.tables.objects.instances import instances
from nylium.tables.objects.types import types


def _seed_type() -> UUID:
    """create_type seeds the builtins; return the type row uuid of "T"."""
    view = Api.create_type("T", {"name": "String"}, "Ts")
    row = next(types.where(name=view.name), None)
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


def test_where_by_type():
    t = _seed_type()
    u1 = _seed_instance(t)
    u2 = _seed_instance(t)
    assert {i.uuid for i in instances.where(type_uuid=t)} >= {u1, u2}


def test_domain_reads():
    t = _seed_type()
    u = _seed_instance(t)
    assert instances[u].name == "instance-1"
    assert instances[u].type_name == "T"
    assert u in instances
    assert uuid4() not in instances
    assert instances.get(u) is not None
    assert instances.get(uuid4()) is None
