"""Server-side session tokens: issue, resolve, revoke."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import ClassVar
from uuid import UUID

from nylium.tables import TABLE_AuthSessions, TABLE_AuthUsers


class sessions:
    """Namespace-only owner (snake_case by doctrine: groups behavior,
    never instantiated)."""

    COOKIE_NAME: ClassVar[str] = "nylium_session"
    TTL: ClassVar[timedelta] = timedelta(days=30)

    @classmethod
    def issue(cls, user_uuid: UUID) -> str:
        """Create a session, return the raw token for the cookie."""
        TABLE_AuthSessions.purge_expired()
        token = secrets.token_urlsafe(32)
        TABLE_AuthSessions.create(user_uuid, cls._hash(token), cls._deadline())
        return token

    @classmethod
    def user_uuid_for(cls, token: str | None) -> UUID | None:
        """Resolve a cookie token to a live user, sliding the expiry."""
        if not token:
            return None
        row = TABLE_AuthSessions.by_hash(cls._hash(token))
        if row is None:
            return None
        if row.expires_at <= datetime.now(timezone.utc):
            TABLE_AuthSessions.delete(row.token_hash)
            return None
        TABLE_AuthSessions.refresh(row.token_hash, cls._deadline())
        return row.user_uuid

    @classmethod
    def user_for(cls, token: str | None) -> TABLE_AuthUsers | None:
        user_uuid = cls.user_uuid_for(token)
        if user_uuid is None:
            return None
        return TABLE_AuthUsers.by_uuid(user_uuid)

    @classmethod
    def revoke(cls, token: str | None) -> None:
        if token:
            TABLE_AuthSessions.delete(cls._hash(token))

    @classmethod
    def _hash(cls, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def _deadline(cls) -> datetime:
        return datetime.now(timezone.utc) + cls.TTL
