# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.auth.auth_credential import AuthCredential as AuthCredential
from nylium.tables.auth.table_auth_credentials import TABLE_AuthCredentials as TABLE_AuthCredentials


class AuthCredentials(Table[UUID, AuthCredential]):
    """The auth_credentials table as a Mapping of writable credentials."""

    __row__: ClassVar[type[Row]] = AuthCredential

    @databasemethod(commit=True)
    def create(
        self,
        user_uuid: UUID,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
        transports: str,
    ) -> AuthCredential:
        row = TABLE_AuthCredentials(
            user_uuid=user_uuid,
            credential_id=credential_id,
            public_key=public_key,
            sign_count=sign_count,
            transports=transports,
        )
        Database.session.add(row)
        Database.session.flush()
        return AuthCredential(row)


auth_credentials = AuthCredentials()
