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
