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

__all__ = ["ceremonies", "require_user", "sessions"]
