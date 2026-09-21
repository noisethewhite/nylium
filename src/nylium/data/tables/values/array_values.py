"""ArrayValues table store for ArrayValue."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
import sqlalchemy as sqla
from nylium.database import Database
from nylium.database.row import Row, mapper
from nylium.database.table import Table
from nylium.data.rows.values.array_value import ArrayValue

class ArrayValues(Table[tuple[UUID, int], ArrayValue]):
    """The array_values table as a store of element rows."""

    __row__: ClassVar[type[Row]] = ArrayValue

    @classmethod
    @Database.use_same_session
    def delete_memberships(cls, value_uuid: UUID) -> None:
        """Drop every array-membership row pointing at the given element uuid."""
        c = mapper(ArrayValue).columns
        _ = Database.execute(sqla.delete(ArrayValue).where(c.value_uuid == value_uuid))

    @classmethod
    @Database.use_same_session
    def element_uuids_of(cls, array_uuid: UUID) -> list[UUID]:
        """Element uuids of one array, in index order (WArray.read relies on
        the ordering; the destroy path just wants the snapshot)."""
        c = mapper(ArrayValue).columns
        return list(
            Database.scalars(
                sqla.select(c.value_uuid)
                .where(c.inst_uuid == array_uuid)
                .order_by(c.index)
            ).all()
        )

    @classmethod
    @Database.use_same_session
    def add_element(cls, array_uuid: UUID, index: int, value_uuid: UUID) -> None:
        """Append one element row (plain insert — _fill rewrites from empty)."""
        Database.add(ArrayValue(inst_uuid=array_uuid, index=index, value_uuid=value_uuid))

    @classmethod
    @Database.use_same_session
    def delete_elements_of(cls, array_uuid: UUID) -> None:
        """Detach every element row of the array and flush — the FK
        array_values.value_uuid -> instances forbids deleting a box that is
        still referenced, so the pointer rows go first."""
        c = mapper(ArrayValue).columns
        _ = Database.execute(sqla.delete(ArrayValue).where(c.inst_uuid == array_uuid))
        Database.flush()

array_values = ArrayValues()
