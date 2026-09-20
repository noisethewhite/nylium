# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database import Database, commit_after_this
from nylium.database.table import Row, Table
from nylium.tables.auth.api_token import ApiToken as ApiToken
from nylium.tables.auth.table_api_tokens import TABLE_ApiTokens as TABLE_ApiTokens


class ApiTokens(Table[UUID, ApiToken]):
    """The api_tokens table as a Mapping of writable tokens."""

    __row__: ClassVar[type[Row]] = ApiToken

    @commit_after_this
    def create(self, user_uuid: UUID, name: str, token_hash: str, scope: str) -> ApiToken:
        row = TABLE_ApiTokens(
            user_uuid=user_uuid, name=name, token_hash=token_hash, scope=scope
        )
        Database.add(row)
        Database.flush()  # populate uuid/created_at before the session ends
        return ApiToken(row)


api_tokens = ApiTokens()
