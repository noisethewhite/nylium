"""File values store — the file-reference statements (ADR-0031).

The statements moved here from ``objects/wfile.py`` (ADR-0030 phase C)
and now live on the ``FileValues`` store. ``TABLE_FileValues`` stays in
``tables/values/file_values.py``.
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.rows.values.file_value import FileValue
from nylium.tables.values.file_values import TABLE_FileValues


class FileValues(Table[tuple[UUID, UUID], FileValue]):
    """The file_values table as a store of file-reference rows."""

    __row__: ClassVar[type[Row]] = FileValue

    @classmethod
    @Database.use_same_session
    def file_ref_for(cls, inst_uuid: UUID, prop_uuid: UUID) -> UUID | None:
        """The file uuid referenced by (owner instance, prop), or None."""
        return Database.scalar(
            sqla.select(TABLE_FileValues.file_uuid).where(
                TABLE_FileValues.inst_uuid == inst_uuid,
                TABLE_FileValues.prop_uuid == prop_uuid,
            )
        )

    @classmethod
    @Database.use_same_session
    def write_ref(
        cls, inst_uuid: UUID, prop_uuid: UUID, file_uuid: UUID | None
    ) -> None:
        """Set/clear the file reference of (owner instance, prop)."""
        if file_uuid is None:
            _ = Database.execute(
                sqla.delete(TABLE_FileValues).where(
                    TABLE_FileValues.inst_uuid == inst_uuid,
                    TABLE_FileValues.prop_uuid == prop_uuid,
                )
            )
            return
        row = Database.get(TABLE_FileValues, (inst_uuid, prop_uuid))
        if row is None:
            Database.add(
                TABLE_FileValues(inst_uuid=inst_uuid, prop_uuid=prop_uuid, file_uuid=file_uuid)
            )
            return
        row.file_uuid = file_uuid


file_values = FileValues()
