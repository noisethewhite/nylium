"""FileValues table store for FileValue."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
import sqlalchemy as sqla
from nylium.database import Database
from nylium.database.Row import Row, get_mapper
from nylium.database.Table import Table
from nylium.data.rows import FileValue

class FileValues(Table[tuple[UUID, UUID], FileValue]):
    """The file_values table as a store of file-reference rows."""

    __row__: ClassVar[type[Row]] = FileValue

    @classmethod
    @Database.use_same_session
    def file_ref_for(cls, inst_uuid: UUID, prop_uuid: UUID) -> UUID | None:
        """The file uuid referenced by (owner instance, prop), or None."""
        c = get_mapper(FileValue).columns
        return Database.scalar(
            sqla.select(c.file_uuid).where(
                c.inst_uuid == inst_uuid, c.prop_uuid == prop_uuid
            )
        )

    @classmethod
    @Database.use_same_session
    def write_ref(
        cls, inst_uuid: UUID, prop_uuid: UUID, file_uuid: UUID | None
    ) -> None:
        """Set/clear the file reference of (owner instance, prop)."""
        c = get_mapper(FileValue).columns
        if file_uuid is None:
            _ = Database.execute(
                sqla.delete(FileValue).where(
                    c.inst_uuid == inst_uuid, c.prop_uuid == prop_uuid
                )
            )
            return
        row = Database.get(FileValue, (inst_uuid, prop_uuid))
        if row is None:
            Database.add(
                FileValue(inst_uuid=inst_uuid, prop_uuid=prop_uuid, file_uuid=file_uuid)
            )
            return
        row.file_uuid = file_uuid

file_values = FileValues()
