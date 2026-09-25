"""FileUUID — typed identifier for a ``File`` row (``files``)."""
from __future__ import annotations

from uuid import UUID

from nylium.data.rows import File
from nylium.data.tables import files


class FileUUID(UUID):
    """A ``files`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "FileUUID":
        return cls(str(value))

    def get(self) -> File | None:
        """The ``File`` row this uuid points at, or ``None`` if it is gone."""
        return files.get(self)
