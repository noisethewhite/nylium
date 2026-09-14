# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.auth.auth_user import AuthUser as AuthUser
from nylium.tables.auth.table_auth_users import TABLE_AuthUsers as TABLE_AuthUsers


class AuthUsers(Table[UUID, AuthUser]):
    """The auth_users table as a Mapping of writable users."""

    __row__: ClassVar[type[Row]] = AuthUser

    @databasemethod(commit=True)
    def create(self, name: str) -> AuthUser:
        """Insert a user, returning its row (uuid/created_at populated by
        the flush)."""
        row = TABLE_AuthUsers(name=name)
        Database.add(row)
        Database.flush()
        return AuthUser(row)


auth_users = AuthUsers()
