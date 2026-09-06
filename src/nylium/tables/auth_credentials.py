from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import BigInteger, DateTime, ForeignKey, LargeBinary, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.tables.base import Base


class AuthCredentials(Base):
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

    @classmethod
    @databasemethod(commit=False)
    def count_all(cls,) -> int:
        return Database.session.scalar(sqla.select(sqla.func.count()).select_from(cls)) or 0

    @classmethod
    @databasemethod(commit=False)
    def by_credential_id(
        cls, credential_id: bytes
    ) -> "AuthCredentials | None":
        return Database.session.scalar(
            sqla.select(cls).where(cls.credential_id == credential_id)
        )

    @classmethod
    @databasemethod(commit=False)
    def credential_ids_for(cls, user_uuid: UUID) -> list[bytes]:
        return list(
            Database.session.scalars(
                sqla.select(cls.credential_id).where(cls.user_uuid == user_uuid)
            ).all()
        )

    @classmethod
    @databasemethod(commit=True)
    def register(
        cls,
        user_uuid: UUID,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
        transports: str,
    ) -> None:
        Database.session.add(
            cls(
                user_uuid=user_uuid,
                credential_id=credential_id,
                public_key=public_key,
                sign_count=sign_count,
                transports=transports,
            )
        )

    @classmethod
    @databasemethod(commit=True)
    def mark_used(cls, uuid: UUID, sign_count: int) -> None:
        row = Database.session.get(cls, uuid)
        if row is not None:
            row.sign_count = sign_count
            row.last_used_at = datetime.now(timezone.utc)
