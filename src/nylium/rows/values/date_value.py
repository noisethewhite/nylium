# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One date cell: a writable snapshot of a TABLE_DateValues row."""
from __future__ import annotations

from datetime import date
from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.values.date_values import TABLE_DateValues


class DateValue(Row):
    """One date cell: a writable snapshot of a TABLE_DateValues row."""

    __table__: ClassVar[type[object]] = TABLE_DateValues

    inst_uuid: UUID
    prop_uuid: UUID
    value: date
