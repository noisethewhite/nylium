from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.tabledomain import TableDomain, TableMapping, tableproperty
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
    # Every instance carries both forms (ADR-0011 phase 8), same rule as
    # types.plural_name; Instances.create derives "<name>s" by default
    plural_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
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


class Instance(TableDomain):
    """One instance: a writable snapshot of a TABLE_Instances row."""

    __table__: ClassVar[type[Base]] = TABLE_Instances

    uuid: tableproperty[Instance, UUID] = tableproperty()
    type_uuid: tableproperty[Instance, UUID] = tableproperty()
    name: tableproperty[Instance, str] = tableproperty()
    plural_name: tableproperty[Instance, str] = tableproperty()
    owner_object_uuid: tableproperty[Instance, UUID | None] = tableproperty()
    owner_prop_uuid: tableproperty[Instance, UUID | None] = tableproperty()
    created_at: tableproperty[Instance, datetime] = tableproperty()
    modified_at: tableproperty[Instance, datetime] = tableproperty()

    @property
    def type_name(self) -> str:
        """The instance's type name; ``<dangling>`` if the type row is gone."""
        t = types.get(self.type_uuid)
        return "<dangling>" if t is None else t.name


def unique_plural_name(uuid: UUID, name: str, plural_name: str | None = None) -> str:
    """Pick a collision-free plural: "<name>s", or "<name>s-<uuid8>" if taken.

    Queries the live session, so rows pending in the current transaction
    (autoflush) count as taken too — matters when one transaction creates
    several same-named instances (nested arrays all named ``array``).
    """
    candidate = plural_name or f"{name}s"
    taken = (
        Database.session.query(TABLE_Instances.uuid)
        .filter_by(plural_name=candidate)
        .first()
    )
    if taken is not None:
        candidate = f"{name}s-{str(uuid)[:8]}"
    return candidate


class Instances(TableMapping[UUID, Instance]):
    """The instances table as a Mapping of writable instances."""

    __domain__: ClassVar[type[TableDomain]] = Instance

    @databasemethod(commit=True)
    def create(
        self,
        uuid: UUID,
        type_uuid: UUID,
        name: str,
        plural_name: str | None = None,
        owner_object_uuid: UUID | None = None,
        owner_prop_uuid: UUID | None = None,
    ) -> None:
        Database.session.add(
            TABLE_Instances(
                uuid=uuid,
                type_uuid=type_uuid,
                name=name,
                plural_name=unique_plural_name(uuid, name, plural_name),
                owner_object_uuid=owner_object_uuid,
                owner_prop_uuid=owner_prop_uuid,
            )
        )
        Database.session.flush()


instances = Instances()
