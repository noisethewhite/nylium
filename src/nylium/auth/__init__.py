"""Passkey (WebAuthn) authentication: ceremonies, sessions, guard.

Deliberately sits BELOW the object layer: credentials live in system
tables (auth_*), not in nylium objects — the type system has no blob
scalar, and auth must work before any user types exist.

Bootstrap policy (ADR-0001): while zero credentials exist, registration
is open and the first passkey becomes the owner. After that, register
requires an authenticated session (adding keys = being logged in).
"""
from .ceremonies import ceremonies
from .guard import require_user
from .sessions import sessions
from nylium.auth.routes import auth_routes
from nylium.auth.guard import require_cookie_user
from nylium.auth.token_routes import token_routes
from nylium.auth.tokens import tokens

__all__ = [
    "auth_routes",
    "ceremonies",
    "require_cookie_user",
    "require_user",
    "sessions",
    "token_routes",
    "tokens",
]
