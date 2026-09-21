"""The time_values table: TimeValue (mapped Row) + TimeValues (store)."""
from __future__ import annotations

from datetime import time
from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey, Time
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.table import Row
from nylium.table_rows.values.scalar_values import ScalarValuesTable
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TimeValue(Row):
    __tablename__: ClassVar[str] = "time_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[time] = mapped_column(Time, nullable=False)


class TimeValues(ScalarValuesTable[TimeValue]):
    """The time_values table as a store of writable time cells."""

    __row__: ClassVar[type[Row]] = TimeValue


time_values = TimeValues()
