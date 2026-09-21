"""The string_values table: StringValue (mapped Row) + StringValues (store)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.table import Row
from nylium.table_rows.values.scalar_values import ScalarValuesTable
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class StringValue(Row):
    __tablename__: ClassVar[str] = "string_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)


class StringValues(ScalarValuesTable[StringValue]):
    """The string_values table as a store of writable string cells."""

    __row__: ClassVar[type[Row]] = StringValue


string_values = StringValues()
