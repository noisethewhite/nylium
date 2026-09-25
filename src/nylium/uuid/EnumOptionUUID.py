"""EnumOptionUUID — typed identifier for a ``EnumOption`` row (``enum_options``)."""
from __future__ import annotations

from uuid import UUID

from pydantic_core import core_schema

from nylium.data.rows import EnumOption
from nylium.data.tables import enum_options


class EnumOptionUUID(UUID):
    """A ``enum_options`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "EnumOptionUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> EnumOption | None:
        """The ``EnumOption`` row this uuid points at, or ``None`` if it is gone."""
        return enum_options.get(self)
