"""TraitDecorUUID — typed identifier for a ``TraitDecor`` row (``trait_decor``)."""
from __future__ import annotations

from uuid import UUID

from nylium.data.rows import TraitDecor
from nylium.data.tables import trait_decor


class TraitDecorUUID(UUID):
    """A ``trait_decor`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "TraitDecorUUID":
        return cls(str(value))

    def get(self) -> TraitDecor | None:
        """The ``TraitDecor`` row this uuid points at, or ``None`` if it is gone."""
        return trait_decor.get(self)
