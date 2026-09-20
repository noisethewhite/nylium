# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One month/day+time cell: a writable snapshot of a TABLE_MonthDayTimeValues row.

The stored value is the ``"MM-DDTHH:MM"`` text stamp (year-less calendar
types have no native column type — ADR-0031 note).
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.values.monthdaytime_values import TABLE_MonthDayTimeValues


class MonthDayTimeValue(Row):
    """One month/day+time cell: a writable snapshot of a TABLE_MonthDayTimeValues row."""

    __table__: ClassVar[type[object]] = TABLE_MonthDayTimeValues

    inst_uuid: UUID
    prop_uuid: UUID
    value: str
