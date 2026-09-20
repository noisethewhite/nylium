# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One numeric cell: a writable snapshot of a TABLE_NumericValues row."""
from __future__ import annotations

from decimal import Decimal
from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.values.numeric_values import TABLE_NumericValues


class NumericValue(Row):
    """One numeric cell: a writable snapshot of a TABLE_NumericValues row."""

    __table__: ClassVar[type[object]] = TABLE_NumericValues

    inst_uuid: UUID
    prop_uuid: UUID
    value: Decimal
    unit: str | None
