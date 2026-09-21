"""The date_values table: DateValue (mapped Row) + DateValues (store)."""
from __future__ import annotations

from datetime import date
from typing import ClassVar
from uuid import UUID

from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.table import Row
from nylium.table_rows.values.scalar_values import ScalarValuesTable
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class DateValue(Row):
    __tablename__: ClassVar[str] = "date_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[date] = mapped_column(Date, nullable=False)


class DateValues(ScalarValuesTable[DateValue]):
    """The date_values table as a store of writable date cells."""

    __row__: ClassVar[type[Row]] = DateValue


date_values = DateValues()
