# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One integer cell: a writable snapshot of a TABLE_IntegerValues row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.values.integer_values import TABLE_IntegerValues


class IntegerValue(Row):
    """One integer cell: a writable snapshot of a TABLE_IntegerValues row."""

    __table__: ClassVar[type[object]] = TABLE_IntegerValues

    inst_uuid: UUID
    prop_uuid: UUID
    value: int
