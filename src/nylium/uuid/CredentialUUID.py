"""CredentialUUID — typed identifier for a ``AuthCredential`` row (``auth_credentials``)."""
from __future__ import annotations

from uuid import UUID

from pydantic_core import core_schema

from nylium.data.rows import AuthCredential
from nylium.data.tables import auth_credentials


class CredentialUUID(UUID):
    """A ``auth_credentials`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "CredentialUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> AuthCredential | None:
        """The ``AuthCredential`` row this uuid points at, or ``None`` if it is gone."""
        return auth_credentials.get(self)
