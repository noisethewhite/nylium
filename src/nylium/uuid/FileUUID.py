"""FileUUID — typed identifier for a ``File`` row (``files``)."""
from __future__ import annotations

from uuid import UUID

import sqlalchemy as sqla
from pydantic_core import core_schema

from nylium.database import Database
from nylium.database.Row import get_mapper
from nylium.data.rows import File, FileValue
from nylium.data.tables import files


class FileUUID(UUID):
    """A ``files`` uuid carrying its own table lookup and reference wiring."""

    @classmethod
    def of(cls, value: UUID) -> "FileUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> File | None:
        """The ``File`` row this uuid points at, or ``None`` if it is gone."""
        return files.get(self)

    @classmethod
    @Database.use_same_session
    def ref_for(cls, inst_uuid: UUID, prop_uuid: UUID) -> "FileUUID | None":
        """The file uuid referenced by (owner instance, prop), or None."""
        c = get_mapper(FileValue).columns
        raw: UUID | None = Database.scalar(
            sqla.select(c.file_uuid).where(c.inst_uuid == inst_uuid, c.prop_uuid == prop_uuid)
        )
        return None if raw is None else cls.of(raw)

    @classmethod
    @Database.use_same_session
    def write_ref(cls, inst_uuid: UUID, prop_uuid: UUID, file_uuid: UUID | None) -> None:
        """Set/clear the file reference of (owner instance, prop)."""
        c = get_mapper(FileValue).columns
        if file_uuid is None:
            _ = Database.execute(
                sqla.delete(FileValue).where(c.inst_uuid == inst_uuid, c.prop_uuid == prop_uuid)
            )
            return
        row = Database.get(FileValue, (inst_uuid, prop_uuid))
        if row is None:
            Database.add(
                FileValue(inst_uuid=inst_uuid, prop_uuid=prop_uuid, file_uuid=file_uuid)
            )
            return
        row.file_uuid = file_uuid
