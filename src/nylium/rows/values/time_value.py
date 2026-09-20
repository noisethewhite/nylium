# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One time cell: a writable snapshot of a TABLE_TimeValues row."""
from __future__ import annotations

from datetime import time
from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.values.time_values import TABLE_TimeValues


class TimeValue(Row):
    """One time cell: a writable snapshot of a TABLE_TimeValues row."""

    __table__: ClassVar[type[object]] = TABLE_TimeValues

    inst_uuid: UUID
    prop_uuid: UUID
    value: time
