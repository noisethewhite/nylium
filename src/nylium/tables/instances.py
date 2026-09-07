from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.store import Store
from nylium.tables.base import Base
from nylium.tables.types import types


class TABLE_Instances(Base):
    """Instances of types — arrays and scalars are types too."""

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


class Instances(Store[UUID, TABLE_Instances]):
    """Instances access layer: rows by uuid, a type_uuid index, and write ops."""

    def __init__(self) -> None:
        super().__init__(TABLE_Instances)

    @databasemethod(commit=False)
    def by_type(self, type_uuid: UUID) -> list[UUID]:
        return list(
            Database.session.scalars(
                sqla.select(TABLE_Instances.uuid).where(
                    TABLE_Instances.type_uuid == type_uuid
                )
            ).all()
        )

    @databasemethod(commit=False)
    def count_of_type(self, type_uuid: UUID) -> int:
        return Database.session.scalar(
            sqla.select(sqla.func.count())
            .select_from(TABLE_Instances)
            .where(TABLE_Instances.type_uuid == type_uuid)
        ) or 0

    @databasemethod(commit=True)
    def create(
        self,
        uuid: UUID,
        type_uuid: UUID,
        name: str,
        owner_object_uuid: UUID | None = None,
        owner_prop_uuid: UUID | None = None,
    ) -> None:
        Database.session.add(
            TABLE_Instances(
                uuid=uuid,
                type_uuid=type_uuid,
                name=name,
                owner_object_uuid=owner_object_uuid,
                owner_prop_uuid=owner_prop_uuid,
            )
        )
        Database.session.flush()

    @databasemethod(commit=False)
    def exists(self, uuid: UUID) -> bool:
        return self.get(uuid) is not None

    @databasemethod(commit=False)
    def get_type_name(self, uuid: UUID) -> str:
        inst = self.get(uuid)
        if inst is None:
            return "<gone>"
        t = types.get(inst.type_uuid)
        return "<dangling>" if t is None else t.name

    @databasemethod(commit=False)
    def type_uuid_of(self, uuid: UUID) -> UUID | None:
        inst = self.get(uuid)
        return None if inst is None else inst.type_uuid

    @databasemethod(commit=False)
    def name_of(self, uuid: UUID) -> str:
        """The registry name of an instance (fallback display title)."""
        inst = self.get(uuid)
        return "" if inst is None else inst.name

    @databasemethod(commit=False)
    def owner_of(self, uuid: UUID) -> tuple[UUID, UUID] | None:
        """(owner object, owner prop) for an embedded instance, else None."""
        inst = self.get(uuid)
        if inst is None or inst.owner_object_uuid is None or inst.owner_prop_uuid is None:
            return None
        return (inst.owner_object_uuid, inst.owner_prop_uuid)


instances = Instances()
