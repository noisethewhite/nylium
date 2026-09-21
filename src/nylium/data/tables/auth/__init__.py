"""Table stores."""
from nylium.data.tables.auth.api_tokens import ApiTokens, api_tokens
from nylium.data.tables.auth.auth_challenges import AuthChallenges, auth_challenges
from nylium.data.tables.auth.auth_credentials import AuthCredentials, auth_credentials
from nylium.data.tables.auth.auth_sessions import AuthSessions, auth_sessions
from nylium.data.tables.auth.auth_users import AuthUsers, auth_users

__all__ = [
    'ApiTokens',
    'api_tokens',
    'AuthChallenges',
    'auth_challenges',
    'AuthCredentials',
    'auth_credentials',
    'AuthSessions',
    'auth_sessions',
    'AuthUsers',
    'auth_users',
]
