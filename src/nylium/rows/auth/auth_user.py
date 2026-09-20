# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.auth.table_auth_users import TABLE_AuthUsers


class AuthUser(Row):
    """One auth user: a writable snapshot of a TABLE_AuthUsers row."""

    __table__: ClassVar[type[object]] = TABLE_AuthUsers

    uuid: UUID
    name: str
    created_at: datetime
