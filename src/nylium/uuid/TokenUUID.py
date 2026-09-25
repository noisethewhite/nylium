"""TokenUUID — typed identifier for a ``ApiToken`` row (``api_tokens``)."""
from __future__ import annotations

from uuid import UUID

from nylium.data.rows import ApiToken
from nylium.data.tables import api_tokens


class TokenUUID(UUID):
    """A ``api_tokens`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "TokenUUID":
        return cls(str(value))

    def get(self) -> ApiToken | None:
        """The ``ApiToken`` row this uuid points at, or ``None`` if it is gone."""
        return api_tokens.get(self)
