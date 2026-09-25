"""TypeDecorUUID — typed identifier for a ``TypeDecor`` row (``type_decor``)."""
from __future__ import annotations

from uuid import UUID

from pydantic_core import core_schema

from nylium.data.rows import TypeDecor
from nylium.data.tables import type_decor


class TypeDecorUUID(UUID):
    """A ``type_decor`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "TypeDecorUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> TypeDecor | None:
        """The ``TypeDecor`` row this uuid points at, or ``None`` if it is gone."""
        return type_decor.get(self)
