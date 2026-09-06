"""HTTP surface for API-token management (ADR-0009 §3).

Minting, listing and revoking tokens is a session-only surface: a bearer
token can read/write the object store but must never create or revoke
tokens, so every endpoint here depends on require_cookie_user (cookie, not
bearer).
"""
from __future__ import annotations

import json
from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, Request
from fastapi.responses import JSONResponse

from nylium.auth.guard import require_cookie_user
from nylium.auth.tokens import tokens
from nylium.database.tables import ApiTokens, AuthUsers
from nylium.server.errors import ValidationError


def _token_view(row: ApiTokens) -> dict[str, object]:
    return {
        "uuid": str(row.uuid),
        "name": row.name,
        "scope": row.scope,
        "created_at": row.created_at.isoformat(),
        "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
    }


class token_routes:
    """Namespace-only owner (snake_case by doctrine: groups behavior,
    never instantiated)."""

    @classmethod
    async def create(
        cls, request: Request, user: Annotated[AuthUsers, Depends(require_cookie_user)]
    ) -> JSONResponse:
        body = await cls._body(request)
        name = body.get("name")
        scope = body.get("scope")
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("token name must be a non-empty string")
        if scope not in (tokens.READ, tokens.READ_WRITE):
            raise ValidationError("token scope must be 'read' or 'read-write'")
        final_name = name.strip()
        final_scope = cast(str, scope)
        uuid, raw = tokens.issue(user.uuid, final_name, final_scope)
        return JSONResponse(
            {
                "uuid": str(uuid),
                "name": final_name,
                "scope": final_scope,
                "token": raw,
            },
            status_code=201,
        )

    @classmethod
    def list(cls, user: Annotated[AuthUsers, Depends(require_cookie_user)]) -> JSONResponse:
        return JSONResponse([_token_view(row) for row in ApiTokens.for_user(user.uuid)])

    @classmethod
    def revoke(
        cls, token_uuid: UUID, user: Annotated[AuthUsers, Depends(require_cookie_user)]
    ) -> JSONResponse:
        if not ApiTokens.revoke(user.uuid, token_uuid):
            raise KeyError(f"no token {token_uuid}")
        return JSONResponse({"ok": True})

    # --- internals ---

    @classmethod
    async def _body(cls, request: Request) -> dict[str, object]:
        raw = await request.body()
        if not raw:
            return {}
        parsed = cast(object, json.loads(raw.decode()))
        if not isinstance(parsed, dict):
            raise ValidationError("malformed request")
        return cast(dict[str, object], parsed)
