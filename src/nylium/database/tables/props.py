from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, Session, mapped_column

from nylium.database.database import Database
from nylium.database.tables.base import Base
from nylium.database.tables.types import Types


class Props(Base):
    __tablename__: str = "props"
    __table_args__: tuple[UniqueConstraint, ...] = (
        # One key can't be defined twice on the same owner type
        UniqueConstraint("owner_type_uuid", "key"),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    owner_type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=False
    )
    value_type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid"), nullable=False
    )
    # the prop's slot in the owner type's display order — create order
    # unless a reorder overwrote it
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def get_type_name(cls, session: Session, owner_type_uuid: UUID, key: str) -> str:
        row = session.scalar(
            sqla.select(cls).where(
                cls.owner_type_uuid == owner_type_uuid, cls.key == key
            )
        )
        if row is None:
            raise KeyError(f"type {Types.name_by_uuid(owner_type_uuid)!r} has no prop {key!r}")
        value_type = Types.name_by_uuid(row.value_type_uuid)
        if value_type is None:
            raise KeyError(f"Type with UUID {row.value_type_uuid} does not exist")
        return value_type
