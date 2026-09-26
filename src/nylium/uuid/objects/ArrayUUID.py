"""ArrayUUID — an ObjectUUID that only accepts ``Array<...>`` instances."""
from __future__ import annotations

from typing import Self, override
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.Row import get_mapper
from nylium.data.rows import ArrayValue
from nylium.data.tables import instances, types
from nylium.uuid.ObjectUUID import ObjectUUID


class ArrayUUID(ObjectUUID):
    """An instance uuid whose instance is an ``Array<...>``."""

    @classmethod
    @override
    def of(cls, value: UUID) -> Self:
        inst = instances.get(value)
        if inst is None:
            raise KeyError(f"no instance {value}")
        t = types.get(inst.type_uuid)
        if t is None or not t.name.startswith("Array<"):
            raise TypeError(f"{value} is not an Array<...> instance")
        return cls(str(value))

    @Database.use_same_session
    def element_uuids_of(self) -> list[UUID]:
        """Element uuids of this array, in index order."""
        c = get_mapper(ArrayValue).columns
        return list(
            Database.scalars(
                sqla.select(c.value_uuid)
                .where(c.inst_uuid == self)
                .order_by(c.index)
            ).all()
        )

    @Database.use_same_session
    def add_element(self, index: int, value_uuid: UUID) -> None:
        """Append one element row (plain insert — _fill rewrites from empty)."""
        Database.add(ArrayValue(inst_uuid=self, index=index, value_uuid=value_uuid))

    @Database.use_same_session
    def delete_elements_of(self) -> None:
        """Detach every element row of the array and flush."""
        c = get_mapper(ArrayValue).columns
        _ = Database.execute(sqla.delete(ArrayValue).where(c.inst_uuid == self))
        Database.flush()
