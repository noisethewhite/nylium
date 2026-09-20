# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One string cell: a writable snapshot of a TABLE_StringValues row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.values.string_values import TABLE_StringValues


class StringValue(Row):
    """One string cell: a writable snapshot of a TABLE_StringValues row."""

    __table__: ClassVar[type[object]] = TABLE_StringValues

    inst_uuid: UUID
    prop_uuid: UUID
    value: str
