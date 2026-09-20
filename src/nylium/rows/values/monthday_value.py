# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One month/day cell: a writable snapshot of a TABLE_MonthDayValues row.

The stored value is the ``"MM-DD"`` text stamp (year-less calendar types
have no native column type — ADR-0031 note).
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.values.monthday_values import TABLE_MonthDayValues


class MonthDayValue(Row):
    """One month/day cell: a writable snapshot of a TABLE_MonthDayValues row."""

    __table__: ClassVar[type[object]] = TABLE_MonthDayValues

    inst_uuid: UUID
    prop_uuid: UUID
    value: str
