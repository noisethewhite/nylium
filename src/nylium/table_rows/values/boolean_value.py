"""The boolean_values table: BooleanValue (mapped Row) + BooleanValues (store)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.table import Row
from nylium.table_rows.values.scalar_values import ScalarValuesTable
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class BooleanValue(Row):
    __tablename__: ClassVar[str] = "boolean_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[bool] = mapped_column(nullable=False)


class BooleanValues(ScalarValuesTable[BooleanValue]):
    """The boolean_values table as a store of writable boolean cells."""

    __row__: ClassVar[type[Row]] = BooleanValue


boolean_values = BooleanValues()
