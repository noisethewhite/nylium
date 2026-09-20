# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One array element: a writable snapshot of a TABLE_ArrayValues row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.values.array_values import TABLE_ArrayValues


class ArrayValue(Row):
    """One array element: a writable snapshot of a TABLE_ArrayValues row."""

    __table__: ClassVar[type[object]] = TABLE_ArrayValues

    inst_uuid: UUID
    index: int
    value_uuid: UUID
