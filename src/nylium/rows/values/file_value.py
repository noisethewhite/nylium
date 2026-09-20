# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One file reference: a writable snapshot of a TABLE_FileValues row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.values.file_values import TABLE_FileValues


class FileValue(Row):
    """One file reference: a writable snapshot of a TABLE_FileValues row."""

    __table__: ClassVar[type[object]] = TABLE_FileValues

    file_uuid: UUID
    inst_uuid: UUID
    prop_uuid: UUID
