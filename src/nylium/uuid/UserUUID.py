"""UserUUID — typed identifier for a ``AuthUser`` row (``auth_users``)."""
from __future__ import annotations

from uuid import UUID

from pydantic_core import core_schema

from nylium.data.rows import AuthUser
from nylium.data.tables import auth_users


class UserUUID(UUID):
    """A ``auth_users`` uuid carrying its own table lookup."""

    @classmethod
    def of(cls, value: UUID) -> "UserUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> AuthUser | None:
        """The ``AuthUser`` row this uuid points at, or ``None`` if it is gone."""
        return auth_users.get(self)
