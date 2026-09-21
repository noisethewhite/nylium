"""AuthCredentials table store for AuthCredential."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.rows.auth.auth_credential import AuthCredential

class AuthCredentials(Table[UUID, AuthCredential]):
    """The auth_credentials table as a Mapping of writable credentials."""

    __row__: ClassVar[type[Row]] = AuthCredential

    @Database.commit_after_this
    def create(
        self,
        user_uuid: UUID,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
        transports: str,
    ) -> AuthCredential:
        row = AuthCredential(
            user_uuid=user_uuid,
            credential_id=credential_id,
            public_key=public_key,
            sign_count=sign_count,
            transports=transports,
        )
        Database.add(row)
        Database.flush()
        return row

auth_credentials = AuthCredentials()
