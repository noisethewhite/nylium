# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.auth.table_auth_credentials import TABLE_AuthCredentials


class AuthCredential(Row):
    """One passkey credential: a writable snapshot of an auth_credentials row."""

    __table__: ClassVar[type[object]] = TABLE_AuthCredentials

    uuid: UUID
    user_uuid: UUID
    credential_id: bytes
    public_key: bytes
    sign_count: int
    transports: str
    created_at: datetime
    last_used_at: datetime | None
