"""FunctionUUID — typed reference to a ``FunctionNode`` row (``function_nodes``)."""
from __future__ import annotations

from typing import override

from nylium.data.rows import FunctionNode
from nylium.data.tables import function_nodes
from nylium.uuid.NyRef import NyRef


class FunctionUUID(NyRef):
    """A ``function_nodes`` reference carrying its own table lookup."""

    @override
    def get(self) -> FunctionNode | None:
        """The ``FunctionNode`` row this reference points at, or ``None`` if it is gone."""
        return function_nodes.get(self._uuid)
