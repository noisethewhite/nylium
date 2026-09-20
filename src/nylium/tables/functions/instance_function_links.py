# Instance-level function binding (ADR-0029): which function computes a
# specific prop of a specific object. Keyed by (inst_uuid, prop_uuid) —
# "one function per (owner, prop)" — mirroring instance_values' link
# shape, but the target is a Function<T,R> instance instead of an object.
# This replaces the type-level props.function_uuid column: different
# instances of one type may bind different functions (or none).
from uuid import UUID

import sqlalchemy as sqla
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database
from nylium.tables.base import reg
from typing import ClassVar


@reg.mapped_as_dataclass
class TABLE_InstanceFunctionLinks:
    __tablename__: ClassVar[str] = "instance_function_links"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    function_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False, index=True
    )


@Database.use_same_session
def function_link_for(inst_uuid: UUID, prop_uuid: UUID) -> TABLE_InstanceFunctionLinks | None:
    """The function bound to (owner instance, prop), or None."""
    return Database.scalar(
        sqla.select(TABLE_InstanceFunctionLinks).where(
            TABLE_InstanceFunctionLinks.inst_uuid == inst_uuid,
            TABLE_InstanceFunctionLinks.prop_uuid == prop_uuid,
        )
    )


@Database.use_same_session
def function_uuid_for(inst_uuid: UUID, prop_uuid: UUID) -> UUID | None:
    """The uuid of the function bound to (owner instance, prop), or None."""
    row = function_link_for(inst_uuid, prop_uuid)
    return None if row is None else row.function_uuid


@Database.use_same_session
def merge_function_link(inst_uuid: UUID, prop_uuid: UUID, function_uuid: UUID) -> None:
    """Insert-or-replace the (owner, prop) -> function binding."""
    _ = Database.merge(
        TABLE_InstanceFunctionLinks(
            inst_uuid=inst_uuid, prop_uuid=prop_uuid, function_uuid=function_uuid
        )
    )


@Database.use_same_session
def delete_function_link(inst_uuid: UUID, prop_uuid: UUID) -> None:
    """Remove the (owner, prop) -> function binding, if any."""
    _ = Database.execute(
        sqla.delete(TABLE_InstanceFunctionLinks).where(
            TABLE_InstanceFunctionLinks.inst_uuid == inst_uuid,
            TABLE_InstanceFunctionLinks.prop_uuid == prop_uuid,
        )
    )


@Database.use_same_session
def delete_links_to_function(function_uuid: UUID) -> None:
    """Drop every binding pointing at the given function (on delete)."""
    _ = Database.execute(
        sqla.delete(TABLE_InstanceFunctionLinks).where(
            TABLE_InstanceFunctionLinks.function_uuid == function_uuid
        )
    )


@Database.use_same_session
def function_links_of_instance(inst_uuid: UUID) -> list[tuple[UUID, UUID]]:
    """(prop_uuid, function_uuid) pairs bound on the given instance."""
    rows = Database.execute(
        sqla.select(
            TABLE_InstanceFunctionLinks.prop_uuid,
            TABLE_InstanceFunctionLinks.function_uuid,
        ).where(TABLE_InstanceFunctionLinks.inst_uuid == inst_uuid)
    ).all()
    return [(row[0], row[1]) for row in rows]


@Database.use_same_session
def instance_uuids_bound_to(function_uuid: UUID) -> list[UUID]:
    """Every owner instance that binds the given function (for re-running
    the local cycle check after a function's DAG changes)."""
    rows = Database.execute(
        sqla.select(TABLE_InstanceFunctionLinks.inst_uuid).where(
            TABLE_InstanceFunctionLinks.function_uuid == function_uuid
        )
    ).all()
    return [row[0] for row in rows]
