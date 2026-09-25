"""EnumOptionUUID — typed identifier for a ``EnumOption`` row (``enum_options``)."""
from __future__ import annotations

from uuid import UUID

from nylium.data.rows import EnumOption
from nylium.data.tables import enum_options


class EnumOptionUUID(UUID):
    """A ``enum_options`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "EnumOptionUUID":
        return cls(str(value))

    def get(self) -> EnumOption | None:
        """The ``EnumOption`` row this uuid points at, or ``None`` if it is gone."""
        return enum_options.get(self)
