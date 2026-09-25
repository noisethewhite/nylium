"""CredentialUUID — typed identifier for a ``AuthCredential`` row (``auth_credentials``)."""
from __future__ import annotations

from uuid import UUID

from nylium.data.rows import AuthCredential
from nylium.data.tables import auth_credentials


class CredentialUUID(UUID):
    """A ``auth_credentials`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "CredentialUUID":
        return cls(str(value))

    def get(self) -> AuthCredential | None:
        """The ``AuthCredential`` row this uuid points at, or ``None`` if it is gone."""
        return auth_credentials.get(self)
