"""FunctionUUID — typed identifier for a ``FunctionNode`` row (``function_nodes``)."""
from __future__ import annotations

from uuid import UUID

from nylium.data.rows import FunctionNode
from nylium.data.tables import function_nodes


class FunctionUUID(UUID):
    """A ``function_nodes`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "FunctionUUID":
        return cls(str(value))

    def get(self) -> FunctionNode | None:
        """The ``FunctionNode`` row this uuid points at, or ``None`` if it is gone."""
        return function_nodes.get(self)
