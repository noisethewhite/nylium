"""UnitParts table store for UnitPart."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from nylium.database.table import Row, Table
from nylium.rows.objects.unit_part import UnitPart

class UnitParts(Table[UUID, UnitPart]):
    """The unit_parts table as a Mapping of writable parts."""

    __row__: ClassVar[type[Row]] = UnitPart

unit_parts = UnitParts()
