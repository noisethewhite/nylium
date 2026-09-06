"""API access tokens (ADR-0009 §3): issue, resolve, hash.

The session layer (`sessions`) is for human browser login; this is the
programmatic twin — a raw bearer token is generated once, shown once, and
only its sha256 is stored. Resolution slides nothing and never returns the
raw token; it only confirms a live, unrevoked row and stamps last_used_at.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import ClassVar
from uuid import UUID

from nylium.tables import ApiTokens


class tokens:
    """Namespace-only owner (snake_case by doctrine: groups behavior,
    never instantiated)."""

    READ: ClassVar[str] = "read"
    READ_WRITE: ClassVar[str] = "read-write"

    @classmethod
    def issue(cls, user_uuid: UUID, name: str, scope: str) -> tuple[UUID, str]:
        """Create a token, returning (uuid, raw) — raw is shown once."""
        raw = secrets.token_urlsafe(32)
        row = ApiTokens.create(user_uuid, name, cls.hash_token(raw), scope)
        return row.uuid, raw

    @classmethod
    def resolve(cls, raw: str) -> "ApiTokens | None":
        """Resolve a raw token to its live row (revoked -> None)."""
        row = ApiTokens.by_hash(cls.hash_token(raw))
        if row is None or row.revoked_at is not None:
            return None
        ApiTokens.mark_used(row.uuid)
        return row

    @classmethod
    def hash_token(cls, raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()
