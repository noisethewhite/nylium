"""UnitPartUUID — typed identifier for a ``UnitPart`` row (``unit_parts``)."""
from __future__ import annotations

from uuid import UUID

from nylium.data.rows import UnitPart
from nylium.data.tables import unit_parts


class UnitPartUUID(UUID):
    """A ``unit_parts`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "UnitPartUUID":
        return cls(str(value))

    def get(self) -> UnitPart | None:
        """The ``UnitPart`` row this uuid points at, or ``None`` if it is gone."""
        return unit_parts.get(self)
