"""Table stores."""
from nylium.data.tables.auth.ApiTokens import ApiTokens, api_tokens
from nylium.data.tables.auth.AuthChallenges import AuthChallenges, auth_challenges
from nylium.data.tables.auth.AuthCredentials import AuthCredentials, auth_credentials
from nylium.data.tables.auth.AuthSessions import AuthSessions, auth_sessions
from nylium.data.tables.auth.AuthUsers import AuthUsers, auth_users

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
