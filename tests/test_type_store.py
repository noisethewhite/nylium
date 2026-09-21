"""TypeStore: the Mapping contract over the types table (ADR-0010).

``types`` must behave like ``Mapping[UUID, Type]`` (plus a name index):
``types[uuid]``, ``types.get``, ``uuid in types``, ``iter(types)``,
``len(types)``, ``types.all()`` / ``types.where(...)`` lookups, and
auto-persisting row attribute writes / ``delete`` write ops.
"""
from uuid import UUID, uuid4

import pytest

from nylium.api import Api
from nylium.table_rows.objects import types


def _seed() -> UUID:
    """create_type seeds the builtins; return the uuid of "T"."""
    view = Api.create_type("T", {"name": "String"}, "Ts")
    row = next(types.where(name=view.name), None)
    assert row is not None
    return row.uuid


def test_getitem_returns_row_and_raises_on_missing():
    uuid = _seed()
    assert types[uuid].name == "T"

    with pytest.raises(KeyError):
        _ = types[uuid4()]


def test_get_and_contains():
    uuid = _seed()
    assert types.get(uuid) is not None
    assert types.get(uuid4()) is None
    assert uuid in types
    assert uuid4() not in types


def test_where_second_index():
    uuid = _seed()
    row = next(types.where(name="T"), None)
    assert row is not None
    assert row.uuid == uuid
    assert next(types.where(name="no-such-type"), None) is None


def test_iter_len_all():
    _seed()
    all_rows = list(types.all())
    assert any(row.name == "T" for row in all_rows)

    assert len(types) == len(all_rows)
    # iteration yields the primary keys (uuids)
    assert set(iter(types)) == {row.uuid for row in all_rows}


def test_update_and_delete():
    from nylium.tables.decor import type_decor

    uuid = _seed()
    row = types[uuid]
    row.name = "T2"
    decor = type_decor[uuid]
    decor.plural_name = "T2s"
    decor.icon = "inventory_2"
    decor.color = "#112233"
    assert types[uuid].name == "T2"
    assert type_decor[uuid].plural_name == "T2s"
    assert type_decor[uuid].color == "#112233"

    types.delete(uuid)  # its props + decor cascade via FK ondelete
    assert types.get(uuid) is None
    assert type_decor.get(uuid) is None
    assert next(types.where(name="T2"), None) is None
