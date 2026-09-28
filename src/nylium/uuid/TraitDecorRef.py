"""TraitDecorRef — typed reference to a ``TraitStyle`` row (``trait_style``)."""
from __future__ import annotations

from typing import override

from nylium.data.rows import TraitStyle
from nylium.data.tables import trait_style
from nylium.uuid.NyRef import NyRef


class TraitDecorRef(NyRef):
    """A ``trait_style`` reference carrying its own table lookup."""

    @override
    def get(self) -> TraitStyle | None:
        """The ``TraitStyle`` row this reference points at, or ``None`` if it is gone."""
        return trait_style.get(self._uuid)
