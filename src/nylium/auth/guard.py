"""FastAPI dependency: reject unauthenticated requests on /api routes.

Accept two credential kinds: the existing session cookie and an
`Authorization: Bearer <token>` header (ADR-0009 §3). A token
authenticates as its owning user and is scope-enforced here — a 'read'
token may only drive GET/HEAD.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from nylium.auth.sessions import sessions
from nylium.auth.tokens import tokens
from nylium.tables import auth_users
from nylium.tables.auth_users import AuthUser


@dataclass
class _Credential:
    user: AuthUser
    via_cookie: bool
    scope: str | None


_BEARER_PREFIX = "Bearer "


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization")
    if header is None or not header.startswith(_BEARER_PREFIX):
        return None
    raw = header[len(_BEARER_PREFIX):].strip()
    return raw or None


def _resolve(request: Request) -> _Credential | None:
    raw = _bearer_token(request)
    if raw is not None:
        row = tokens.resolve(raw)
        if row is None:
            return None
        user = auth_users.get(row.user_uuid)
        if user is None:
            return None
        return _Credential(user, False, row.scope)
    user = sessions.user_for(request.cookies.get(sessions.COOKIE_NAME))
    if user is None:
        return None
    return _Credential(user, True, None)


def require_user(request: Request) -> AuthUser:
    # HTTPException is fine here: errors.register maps it onto the
    # uniform {"error": ...} wire shape. Importing ApiError subclasses
    # would create a circular import (server package -> app -> guard).
    credential = _resolve(request)
    if credential is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="authentication required"
        )
    if credential.scope == "read" and request.method not in ("GET", "HEAD"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="read-only token")
    return credential.user


def require_cookie_user(request: Request) -> AuthUser:
    """Session-only guard: a bearer token must never mint/revoke tokens,
    so the token-management surface depends on this instead of require_user."""
    credential = _resolve(request)
    if credential is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="authentication required"
        )
    if not credential.via_cookie:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="session required")
    return credential.user
