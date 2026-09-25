"""FunctionEdgeUUID — typed identifier for a ``FunctionEdge`` row (``function_edges``)."""
from __future__ import annotations

from uuid import UUID

from pydantic_core import core_schema

from nylium.data.rows import FunctionEdge
from nylium.data.tables import function_edges


class FunctionEdgeUUID(UUID):
    """A ``function_edges`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "FunctionEdgeUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> FunctionEdge | None:
        """The ``FunctionEdge`` row this uuid points at, or ``None`` if it is gone."""
        return function_edges.get(self)
