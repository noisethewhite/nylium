"""The array_values table: ArrayValue (mapped Row) + ArrayValues (store).

Array elements: the array itself is an instance (of an array type); rows
map (array instance, index) -> element. The element is either a box
instance (scalar/nested-array), a referenced user-type instance, or — for
Array<File/Document/Image> (ADR-0008) — a files.uuid. So value_uuid is a
bare uuid, not an FK: files aren't instances and would violate the
instances FK. Cleanup is manual in WArray, not DB-cascaded.

Cross-table projections (tag chips, collect ranges) live in
``nylium.objects.navigation`` — a table store never imports a sibling
table (ADR-0033).
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.row import Row, mapper
from nylium.database.table import Table
from nylium.tables.base import reg
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column


@reg.mapped_as_dataclass
class ArrayValue(Row):
    __tablename__: ClassVar[str] = "array_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    index: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_uuid: Mapped[UUID] = mapped_column(nullable=False)


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
