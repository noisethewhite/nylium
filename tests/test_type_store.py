"""TypeStore: the Mapping contract over the types table (ADR-0010).

``types`` must behave like ``dict[UUID, TypesRow]`` (plus a name index):
``types[uuid]``, ``types.get``, ``uuid in types``, ``iter(types)``,
``len(types)``, ``types.all()`` and the ``by_name`` / ``update`` /
``delete`` write ops.
"""
from uuid import UUID, uuid4

import pytest

from nylium.api import Api
from nylium.tables.types import types


def _seed() -> UUID:
    """create_type seeds the builtins; return the uuid of "T"."""
    view = Api.create_type("T", {"name": "String"}, "Ts")
    row = types.by_name(view.name)
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


def test_by_name_second_index():
    uuid = _seed()
    row = types.by_name("T")
    assert row is not None
    assert row.uuid == uuid
    assert types.by_name("no-such-type") is None


def test_iter_len_all():
    _seed()
    all_rows = types.all()
    assert any(row.name == "T" for row in all_rows)

    assert len(types) == len(all_rows)
    # iteration yields the primary keys (uuids)
    assert set(iter(types)) == {row.uuid for row in all_rows}


def test_update_and_delete():
    uuid = _seed()
    types.update(uuid, "T2", "T2s", "inventory_2", "#112233")
    assert types[uuid].name == "T2"
    assert types[uuid].plural_name == "T2s"
    assert types[uuid].color == "#112233"

    types.delete(uuid)  # its props cascade via FK ondelete
    assert types.get(uuid) is None
    assert types.by_name("T2") is None
