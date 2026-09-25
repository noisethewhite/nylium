"""FileUUID — typed identifier for a ``File`` row (``files``)."""
from __future__ import annotations

from uuid import UUID

from pydantic_core import core_schema

from nylium.data.rows import File
from nylium.data.tables import files


class FileUUID(UUID):
    """A ``files`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "FileUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> File | None:
        """The ``File`` row this uuid points at, or ``None`` if it is gone."""
        return files.get(self)
