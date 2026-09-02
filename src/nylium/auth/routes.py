"""HTTP surface for passkey auth. The only unauthenticated /api routes
in the app — everything else sits behind require_user."""
from __future__ import annotations

import json
from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.responses import JSONResponse

from nylium.auth.ceremonies import ceremonies
from nylium.auth.guard import require_user
from nylium.auth.sessions import sessions
from nylium.database.tables import AuthUsers
from nylium.system.environment import Environment


class auth_routes:
    """Namespace-only owner (snake_case by doctrine: groups behavior,
    never instantiated)."""

    @classmethod
    async def register_start(cls, request: Request) -> JSONResponse:
        body = await cls._body(request)
        name = body.get("name")
        if name is not None and not isinstance(name, str):
            raise PermissionError("malformed request")
        current = sessions.user_for(request.cookies.get(sessions.COOKIE_NAME))
        options = ceremonies.register_start(
            name, current.uuid if current is not None else None
        )
        return JSONResponse(json.loads(options))

    @classmethod
    async def register_finish(cls, request: Request) -> JSONResponse:
        token = ceremonies.register_finish((await request.body()).decode())
        return cls._with_session(JSONResponse({"ok": True}), token)

    @classmethod
    async def login_start(cls) -> JSONResponse:
        return JSONResponse(json.loads(ceremonies.login_start()))

    @classmethod
    async def login_finish(cls, request: Request) -> JSONResponse:
        token = ceremonies.login_finish((await request.body()).decode())
        return cls._with_session(JSONResponse({"ok": True}), token)

    @classmethod
    async def logout(cls, request: Request) -> JSONResponse:
        sessions.revoke(request.cookies.get(sessions.COOKIE_NAME))
        response = JSONResponse({"ok": True})
        response.delete_cookie(sessions.COOKIE_NAME)
        return response

    @classmethod
    async def me(
        cls, user: Annotated[AuthUsers, Depends(require_user)]
    ) -> JSONResponse:
        return JSONResponse({"name": user.name})

    # --- internals ---

    @classmethod
    async def _body(cls, request: Request) -> dict[str, object]:
        raw = await request.body()
        if not raw:
            return {}
        parsed = cast(object, json.loads(raw.decode()))
        if not isinstance(parsed, dict):
            raise PermissionError("malformed request")
        return cast(dict[str, object], parsed)

    @classmethod
    def _with_session(cls, response: JSONResponse, token: str) -> JSONResponse:
        response.set_cookie(
            sessions.COOKIE_NAME,
            token,
            max_age=int(sessions.TTL.total_seconds()),
            httponly=True,
            secure=str(Environment.rp_origin).startswith("https://"),
            samesite="lax",
        )
        return response
