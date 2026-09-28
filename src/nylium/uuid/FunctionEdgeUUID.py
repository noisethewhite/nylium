"""FunctionEdgeUUID — typed reference to a ``FunctionEdge`` row (``function_edges``)."""
from __future__ import annotations

from typing import override

from nylium.data.rows import FunctionEdge
from nylium.data.tables import function_edges
from nylium.uuid.NyRef import NyRef


class FunctionEdgeUUID(NyRef):
    """A ``function_edges`` reference carrying its own table lookup."""

    @override
    def get(self) -> FunctionEdge | None:
        """The ``FunctionEdge`` row this reference points at, or ``None`` if it is gone."""
        return function_edges.get(self._uuid)
