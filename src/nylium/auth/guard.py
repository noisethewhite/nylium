"""FastAPI dependency: reject unauthenticated requests on /api routes."""
from __future__ import annotations

from fastapi import HTTPException, Request, status

from nylium.auth.sessions import sessions
from nylium.database.tables import AuthUsers


def require_user(request: Request) -> AuthUsers:
    user = sessions.user_for(request.cookies.get(sessions.COOKIE_NAME))
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="authentication required"
        )
    return user
