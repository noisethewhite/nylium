"""Server-side session tokens: issue, resolve, revoke."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import ClassVar
from uuid import UUID

from nylium.tables import auth_sessions, auth_users
from nylium.tables.auth.auth_users import AuthUser


class sessions:
    """Namespace-only owner (snake_case by doctrine: groups behavior,
    never instantiated)."""

    COOKIE_NAME: ClassVar[str] = "nylium_session"
    TTL: ClassVar[timedelta] = timedelta(days=30)

    @classmethod
    def issue(cls, user_uuid: UUID) -> str:
        """Create a session, return the raw token for the cookie."""
        auth_sessions.purge_expired()
        token = secrets.token_urlsafe(32)
        auth_sessions.create(user_uuid, cls._hash(token), cls._deadline())
        return token

    @classmethod
    def user_uuid_for(cls, token: str | None) -> UUID | None:
        """Resolve a cookie token to a live user, sliding the expiry."""
        if not token:
            return None
        row = auth_sessions.get(cls._hash(token))
        if row is None:
            return None
        if row.expires_at <= datetime.now(timezone.utc):
            auth_sessions.delete(row.token_hash)
            return None
        row.expires_at = cls._deadline()
        return row.user_uuid

    @classmethod
    def user_for(cls, token: str | None) -> AuthUser | None:
        user_uuid = cls.user_uuid_for(token)
        if user_uuid is None:
            return None
        return auth_users.get(user_uuid)

    @classmethod
    def revoke(cls, token: str | None) -> None:
        if token:
            auth_sessions.delete(cls._hash(token))

    @classmethod
    def _hash(cls, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def _deadline(cls) -> datetime:
        return datetime.now(timezone.utc) + cls.TTL
