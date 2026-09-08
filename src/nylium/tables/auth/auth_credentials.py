# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, LargeBinary, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.base import Base


class TABLE_AuthCredentials(Base):
    __tablename__: str = "auth_credentials"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=False
    )
    credential_id: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False, unique=True
    )
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    transports: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuthCredential(Row):
    """One passkey credential: a writable snapshot of an auth_credentials row."""

    __table__: ClassVar[type[Base]] = TABLE_AuthCredentials

    uuid: UUID
    user_uuid: UUID
    credential_id: bytes
    public_key: bytes
    sign_count: int
    transports: str
    created_at: datetime
    last_used_at: datetime | None


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
