# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One unit part: a writable snapshot of a TABLE_UnitParts row (Row class only)."""
from __future__ import annotations

from decimal import Decimal
from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.objects.tables.table_unit_parts import TABLE_UnitParts


class UnitPart(Row):
    """One unit part: a writable snapshot of a TABLE_UnitParts row."""

    __table__: ClassVar[type[object]] = TABLE_UnitParts

    uuid: UUID
    type_uuid: UUID
    name: str
    multiplier: Decimal
    offset: Decimal
    is_base: bool
    position: int
