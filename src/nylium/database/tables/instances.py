from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from nylium.database.database import Database
from nylium.database.tables.base import Base
from nylium.database.tables.types import Types


# Instances of types
# (Both arrays and scalars are considered types, too)
class Instances(Base):
    __tablename__: str = "instances"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Ownership read-index for embedded instances (ADR-0004): the
    # instance_values ref is the source of truth, these two columns
    # answer "who owns this child" without a join. NULL on standalone
    # objects, scalar boxes and array instances.
    owner_object_uuid: Mapped[UUID | None] = mapped_column(nullable=True)
    owner_prop_uuid: Mapped[UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def get_type_name(cls, session: Session, uuid: UUID) -> str:
        inst = session.get(cls, uuid)
        if inst is None:
            return "<gone>"
        name = Types.name_by_uuid(inst.type_uuid)
        return "<dangling>" if name is None else name

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def exists(cls, session: Session, uuid: UUID) -> bool:
        return session.get(cls, uuid) is not None

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def type_uuid_of(cls, session: Session, uuid: UUID) -> UUID | None:
        inst = session.get(cls, uuid)
        return None if inst is None else inst.type_uuid

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def uuids_of_type(cls, session: Session, type_uuid: UUID) -> list[UUID]:
        return list(
            session.scalars(
                sqla.select(cls.uuid).where(cls.type_uuid == type_uuid)
            ).all()
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def count_of_type(cls, session: Session, type_uuid: UUID) -> int:
        return session.scalar(
            sqla.select(sqla.func.count())
            .select_from(cls)
            .where(cls.type_uuid == type_uuid)
        ) or 0

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def register(
        cls,
        session: Session,
        uuid: UUID,
        type_uuid: UUID,
        name: str,
        owner_object_uuid: UUID | None = None,
        owner_prop_uuid: UUID | None = None,
    ) -> None:
        session.add(
            cls(
                uuid=uuid,
                type_uuid=type_uuid,
                name=name,
                owner_object_uuid=owner_object_uuid,
                owner_prop_uuid=owner_prop_uuid,
            )
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def owner_of(cls, session: Session, uuid: UUID) -> "tuple[UUID, UUID] | None":
        """(owner object, owner prop) for an embedded instance, else None."""
        inst = session.get(cls, uuid)
        if inst is None or inst.owner_object_uuid is None or inst.owner_prop_uuid is None:
            return None
        return (inst.owner_object_uuid, inst.owner_prop_uuid)
