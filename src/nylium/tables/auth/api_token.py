# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.auth.table_api_tokens import TABLE_ApiTokens


class ApiToken(Row):
    """One API token: a writable snapshot of an api_tokens row."""

    __table__: ClassVar[type[object]] = TABLE_ApiTokens

    uuid: UUID
    user_uuid: UUID
    name: str
    token_hash: str
    scope: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
