# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One enum option: a writable snapshot of a TABLE_EnumOptions row (Row class only)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.objects.table_enum_options import TABLE_EnumOptions


class EnumOption(Row):
    """One enum option: a writable snapshot of a TABLE_EnumOptions row."""

    __table__: ClassVar[type[object]] = TABLE_EnumOptions

    uuid: UUID
    type_uuid: UUID
    value: str
    position: int

    def wire(self) -> dict[str, object]:
        """The JSON-safe wire shape, matching web/src/contracts.ts
        EnumOptionView."""
        return {"uuid": str(self.uuid), "value": self.value}
