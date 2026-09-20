# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.auth.table_auth_sessions import TABLE_AuthSessions


class AuthSession(Row):
    """One server-side session: a writable snapshot of an auth_sessions row."""

    __table__: ClassVar[type[object]] = TABLE_AuthSessions

    token_hash: str
    user_uuid: UUID
    expires_at: datetime
