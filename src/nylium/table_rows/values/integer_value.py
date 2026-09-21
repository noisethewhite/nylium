"""The integer_values table: IntegerValue (mapped Row) + IntegerValues (store)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.table import Row
from nylium.table_rows.values.scalar_values import ScalarValuesTable
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class IntegerValue(Row):
    __tablename__: ClassVar[str] = "integer_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False)


class IntegerValues(ScalarValuesTable[IntegerValue]):
    """The integer_values table as a store of writable integer cells."""

    __row__: ClassVar[type[Row]] = IntegerValue


integer_values = IntegerValues()
