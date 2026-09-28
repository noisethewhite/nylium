"""UnitPartRef — typed reference to a ``UnitPart`` row (``unit_parts``)."""
from __future__ import annotations

from typing import override

from nylium.data.rows import UnitPart
from nylium.data.tables import unit_parts
from nylium.uuid.NyRef import NyRef


class UnitPartRef(NyRef):
    """A ``unit_parts`` reference carrying its own table lookup."""

    @override
    def get(self) -> UnitPart | None:
        """The ``UnitPart`` row this reference points at, or ``None`` if it is gone."""
        return unit_parts.get(self._uuid)
