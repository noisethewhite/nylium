"""ApiTokens table store for ApiToken."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from nylium.database import Database
from nylium.database.Table import Row, Table
from nylium.data.rows import ApiToken

class ApiTokens(Table[UUID, ApiToken]):
    """The api_tokens table as a Mapping of writable tokens."""

    __row__: ClassVar[type[Row]] = ApiToken

    @Database.commit_after_this
    def create(
        self, user_uuid: UUID, name: str, token_hash: str, scope: str
    ) -> ApiToken:
        row = ApiToken(user_uuid=user_uuid, name=name, token_hash=token_hash, scope=scope)
        Database.add(row)
        Database.flush()
        return row

api_tokens = ApiTokens()
