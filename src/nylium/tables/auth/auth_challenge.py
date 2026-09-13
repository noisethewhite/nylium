# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.auth.table_auth_challenges import TABLE_AuthChallenges


class AuthChallenge(Row):
    """One WebAuthn challenge: a writable snapshot of an auth_challenges row."""

    __table__: ClassVar[type[object]] = TABLE_AuthChallenges

    challenge: bytes
    kind: str
    user_uuid: UUID | None
    expires_at: datetime
