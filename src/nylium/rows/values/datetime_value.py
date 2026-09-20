# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One datetime cell: a writable snapshot of a TABLE_DatetimeValues row."""
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.values.datetime_values import TABLE_DatetimeValues


class DatetimeValue(Row):
    """One datetime cell: a writable snapshot of a TABLE_DatetimeValues row."""

    __table__: ClassVar[type[object]] = TABLE_DatetimeValues

    inst_uuid: UUID
    prop_uuid: UUID
    value: datetime
