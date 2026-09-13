# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.table_files import TABLE_Files


class File(Row):
    """One file: a writable snapshot of a TABLE_Files row."""

    __table__: ClassVar[type[object]] = TABLE_Files

    uuid: UUID
    type_name: str
    name: str
    mime: str
    size_bytes: int

    def wire(self) -> dict[str, object]:
        """The JSON-safe wire shape, matching web/src/contracts.ts FileView."""
        return {
            "uuid": str(self.uuid),
            "type_name": self.type_name,
            "name": self.name,
            "mime": self.mime,
            "size_bytes": self.size_bytes,
        }
