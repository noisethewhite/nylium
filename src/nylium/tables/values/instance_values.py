# Values that are references to other instances (links, nested objects,
# arrays). The referenced instance's own uuid doubles as this row's pk.
# Also hosts the link-statement helpers (ADR-0019): the objects layer
# decides semantics, statements live here.
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from typing import ClassVar

from nylium.database import Database, databasemethod
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TABLE_InstanceValues:
    __tablename__: ClassVar[str] = "instance_values"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), nullable=False
    )
    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False
    )


@databasemethod(commit=False)
def link_for(inst_uuid: UUID, prop_uuid: UUID) -> TABLE_InstanceValues | None:
    """The link row held by (owner instance, prop), or None."""
    return Database.scalar(
        sqla.select(TABLE_InstanceValues).where(
            TABLE_InstanceValues.inst_uuid == inst_uuid,
            TABLE_InstanceValues.prop_uuid == prop_uuid,
        )
    )


@databasemethod(commit=False)
def merge_link(uuid: UUID, prop_uuid: UUID, inst_uuid: UUID) -> None:
    """Insert-or-replace the link row whose pk is the target uuid."""
    _ = Database.merge(
        TABLE_InstanceValues(uuid=uuid, prop_uuid=prop_uuid, inst_uuid=inst_uuid)
    )


@databasemethod(commit=False)
def delete_row(row: TABLE_InstanceValues) -> None:
    """Delete the given link row (already fetched by the caller)."""
    Database.delete(row)


@databasemethod(commit=False)
def delete_links_to(uuid: UUID) -> None:
    """Delete every link row whose target is the given instance uuid."""
    _ = Database.execute(
        sqla.delete(TABLE_InstanceValues).where(TABLE_InstanceValues.uuid == uuid)
    )


@databasemethod(commit=False)
def linked_uuids_of(prop_uuid: UUID) -> list[UUID]:
    """Uuids of every instance linked through the given prop, across all
    owners — the sweep list before an embedded prop is deleted or retyped."""
    return list(
        Database.scalars(
            sqla.select(TABLE_InstanceValues.uuid).where(
                TABLE_InstanceValues.prop_uuid == prop_uuid
            )
        ).all()
    )


@databasemethod(commit=False)
def add_link(uuid: UUID, prop_uuid: UUID, inst_uuid: UUID) -> None:
    """Insert a brand-new link row and flush — the embedded child is a fresh
    uuid4, so this must stay a plain insert (merge would mask a uuid
    collision instead of failing on it). The flush pins insert order:
    instance_values.uuid FKs into instances."""
    Database.add(
        TABLE_InstanceValues(uuid=uuid, prop_uuid=prop_uuid, inst_uuid=inst_uuid)
    )
    Database.flush()


@databasemethod(commit=False)
def array_link_uuids_of(owner_inst_uuid: UUID) -> list[UUID]:
    """Uuids of array-instance links held by the given owner."""
    from nylium.tables.objects.table_props import TABLE_Props
    from nylium.tables.objects.table_types import TABLE_Types

    stmt = (
        sqla.select(TABLE_InstanceValues.uuid)
        .join(TABLE_Props, TABLE_InstanceValues.prop_uuid == TABLE_Props.uuid)
        .join(TABLE_Types, TABLE_Props.value_type_uuid == TABLE_Types.uuid)
        .where(
            TABLE_InstanceValues.inst_uuid == owner_inst_uuid,
            # mirrors WType.ARRAY_TYPE_PREFIX (objects layer imports tables,
            # so the constant cannot flow the other way)
            TABLE_Types.name.like("Array<%"),
        )
    )
    return list(Database.scalars(stmt).all())
