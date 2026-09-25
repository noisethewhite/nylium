"""TokenUUID — typed identifier for a ``ApiToken`` row (``api_tokens``)."""
from __future__ import annotations

from uuid import UUID

from pydantic_core import core_schema

from nylium.data.rows import ApiToken
from nylium.data.tables import api_tokens


class TokenUUID(UUID):
    """A ``api_tokens`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "TokenUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> ApiToken | None:
        """The ``ApiToken`` row this uuid points at, or ``None`` if it is gone."""
        return api_tokens.get(self)
