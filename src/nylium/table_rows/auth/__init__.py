"""Auth tables — mapped Rows + their stores, one file per table (ADR-0033)."""
from nylium.table_rows.auth.api_token import ApiToken, ApiTokens, api_tokens
from nylium.table_rows.auth.auth_challenge import (
    AuthChallenge,
    AuthChallenges,
    auth_challenges,
)
from nylium.table_rows.auth.auth_credential import (
    AuthCredential,
    AuthCredentials,
    auth_credentials,
)
from nylium.table_rows.auth.auth_session import AuthSession, AuthSessions, auth_sessions
from nylium.table_rows.auth.auth_user import AuthUser, AuthUsers, auth_users

__all__ = [
    "ApiToken",
    "ApiTokens",
    "AuthChallenge",
    "AuthChallenges",
    "AuthCredential",
    "AuthCredentials",
    "AuthSession",
    "AuthSessions",
    "AuthUser",
    "AuthUsers",
    "api_tokens",
    "auth_challenges",
    "auth_credentials",
    "auth_sessions",
    "auth_users",
]
