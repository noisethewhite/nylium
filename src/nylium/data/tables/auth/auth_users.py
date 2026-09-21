"""AuthUsers table store for AuthUser."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.data.rows.auth.auth_user import AuthUser

class AuthUsers(Table[UUID, AuthUser]):
    """The auth_users table as a Mapping of writable users."""

    __row__: ClassVar[type[Row]] = AuthUser

    @Database.commit_after_this
    def create(self, name: str) -> AuthUser:
        row = AuthUser(name=name)
        Database.add(row)
        Database.flush()
        return row

auth_users = AuthUsers()
