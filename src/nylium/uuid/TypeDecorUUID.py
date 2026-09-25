"""TypeDecorUUID — typed identifier for a ``TypeStyle`` row (``type_style``)."""
from __future__ import annotations

from uuid import UUID

from pydantic_core import core_schema

from nylium.data.rows import TypeStyle
from nylium.data.tables import type_style


class TypeDecorUUID(UUID):
    """A ``type_style`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "TypeDecorUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> TypeStyle | None:
        """The ``TypeStyle`` row this uuid points at, or ``None`` if it is gone."""
        return type_style.get(self)
