from datetime import datetime, timezone
from typing import ClassVar, cast
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import BigInteger, DateTime, ForeignKey, LargeBinary, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.tabledomain import TableDomain, TableMapping, tableproperty
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


class AuthCredential(TableDomain):
    """One passkey credential: a writable snapshot of an auth_credentials row."""

    __table__: ClassVar[type[Base]] = TABLE_AuthCredentials

    uuid: tableproperty[AuthCredential, UUID] = tableproperty()
    user_uuid: tableproperty[AuthCredential, UUID] = tableproperty()
    credential_id: tableproperty[AuthCredential, bytes] = tableproperty()
    public_key: tableproperty[AuthCredential, bytes] = tableproperty()
    sign_count: tableproperty[AuthCredential, int] = tableproperty()
    transports: tableproperty[AuthCredential, str] = tableproperty()
    created_at: tableproperty[AuthCredential, datetime] = tableproperty()
    last_used_at: tableproperty[AuthCredential, datetime | None] = tableproperty()


class AuthCredentials(TableMapping[UUID, AuthCredential]):
    """The auth_credentials table as a Mapping of writable credentials."""

    __domain__: ClassVar[type[TableDomain]] = AuthCredential

    @databasemethod(commit=False)
    def count_all(self) -> int:
        count = Database.session.scalar(
            sqla.select(sqla.func.count()).select_from(TABLE_AuthCredentials)
        )
        return count or 0

    @databasemethod(commit=False)
    def by_credential_id(self, credential_id: bytes) -> AuthCredential | None:
        row = Database.session.scalar(
            sqla.select(TABLE_AuthCredentials).where(
                TABLE_AuthCredentials.credential_id == credential_id
            )
        )
        return None if row is None else cast(AuthCredential, AuthCredential.from_row(row))

    @databasemethod(commit=False)
    def credential_ids_for(self, user_uuid: UUID) -> list[bytes]:
        return list(
            Database.session.scalars(
                sqla.select(TABLE_AuthCredentials.credential_id).where(
                    TABLE_AuthCredentials.user_uuid == user_uuid
                )
            ).all()
        )

    @databasemethod(commit=True)
    def register(
        self,
        user_uuid: UUID,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
        transports: str,
    ) -> None:
        Database.session.add(
            TABLE_AuthCredentials(
                user_uuid=user_uuid,
                credential_id=credential_id,
                public_key=public_key,
                sign_count=sign_count,
                transports=transports,
            )
        )

    @databasemethod(commit=True)
    def mark_used(self, uuid: UUID, sign_count: int) -> None:
        credential = self.get(uuid)
        if credential is not None:
            credential.sign_count = sign_count
            credential.last_used_at = datetime.now(timezone.utc)


auth_credentials = AuthCredentials()
