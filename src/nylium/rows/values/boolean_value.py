# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One boolean cell: a writable snapshot of a TABLE_BooleanValues row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.values.boolean_values import TABLE_BooleanValues


class BooleanValue(Row):
    """One boolean cell: a writable snapshot of a TABLE_BooleanValues row."""

    __table__: ClassVar[type[object]] = TABLE_BooleanValues

    inst_uuid: UUID
    prop_uuid: UUID
    value: bool
