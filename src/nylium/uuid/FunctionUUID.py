"""FunctionUUID — typed identifier for a ``FunctionNode`` row (``function_nodes``)."""
from __future__ import annotations

from uuid import UUID

from pydantic_core import core_schema

from nylium.data.rows import FunctionNode
from nylium.data.tables import function_nodes


class FunctionUUID(UUID):
    """A ``function_nodes`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "FunctionUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> FunctionNode | None:
        """The ``FunctionNode`` row this uuid points at, or ``None`` if it is gone."""
        return function_nodes.get(self)
