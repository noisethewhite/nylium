"""FunctionEdgeUUID — typed identifier for a ``FunctionEdge`` row (``function_edges``)."""
from __future__ import annotations

from uuid import UUID

from nylium.data.rows import FunctionEdge
from nylium.data.tables import function_edges


class FunctionEdgeUUID(UUID):
    """A ``function_edges`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "FunctionEdgeUUID":
        return cls(str(value))

    def get(self) -> FunctionEdge | None:
        """The ``FunctionEdge`` row this uuid points at, or ``None`` if it is gone."""
        return function_edges.get(self)
