"""TraitDecorUUID — typed identifier for a ``TraitStyle`` row (``trait_style``)."""
from __future__ import annotations

from uuid import UUID

from pydantic_core import core_schema

from nylium.data.rows import TraitStyle
from nylium.data.tables import trait_style


class TraitDecorUUID(UUID):
    """A ``trait_style`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "TraitDecorUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> TraitStyle | None:
        """The ``TraitStyle`` row this uuid points at, or ``None`` if it is gone."""
        return trait_style.get(self)
