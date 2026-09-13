# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.auth.auth_session import AuthSession as AuthSession
from nylium.tables.auth.table_auth_sessions import TABLE_AuthSessions as TABLE_AuthSessions


class AuthSessions(Table[str, AuthSession]):
    """The auth_sessions table as a Mapping keyed by token hash."""

    __row__: ClassVar[type[Row]] = AuthSession

    @databasemethod(commit=True)
    def create(self, user_uuid: UUID, token_hash: str, expires_at: datetime) -> None:
        Database.session.add(
            TABLE_AuthSessions(
                token_hash=token_hash, user_uuid=user_uuid, expires_at=expires_at
            )
        )

    @databasemethod(commit=True)
    def delete(self, token_hash: str) -> None:
        row = Database.session.get(TABLE_AuthSessions, token_hash)
        if row is not None:
            Database.session.delete(row)

    @databasemethod(commit=True)
    def purge_expired(self) -> None:
        _ = Database.session.execute(
            sqla.delete(TABLE_AuthSessions).where(
                TABLE_AuthSessions.expires_at <= datetime.now(timezone.utc)
            )
        )


auth_sessions = AuthSessions()
