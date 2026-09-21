"""The instance_function_links table: InstanceFunctionLink (mapped Row) + store."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.row import mapper
from nylium.database.table import Row, Table
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class InstanceFunctionLink(Row):
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


class InstanceFunctionLinks(Table[tuple[UUID, UUID], InstanceFunctionLink]):
    """The instance_function_links table as a store of function bindings."""

    __row__: ClassVar[type[Row]] = InstanceFunctionLink

    @classmethod
    @Database.use_same_session
    def function_link_for(
        cls, inst_uuid: UUID, prop_uuid: UUID
    ) -> InstanceFunctionLink | None:
        c = mapper(InstanceFunctionLink).columns
        return Database.scalar(
            sqla.select(InstanceFunctionLink).where(
                c.inst_uuid == inst_uuid, c.prop_uuid == prop_uuid
            )
        )

    @classmethod
    @Database.use_same_session
    def function_uuid_for(cls, inst_uuid: UUID, prop_uuid: UUID) -> UUID | None:
        row = cls.function_link_for(inst_uuid, prop_uuid)
        return None if row is None else row.function_uuid

    @classmethod
    @Database.use_same_session
    def merge_function_link(
        cls, inst_uuid: UUID, prop_uuid: UUID, function_uuid: UUID
    ) -> None:
        _ = Database.merge(
            InstanceFunctionLink(
                inst_uuid=inst_uuid, prop_uuid=prop_uuid, function_uuid=function_uuid
            )
        )

    @classmethod
    @Database.use_same_session
    def delete_function_link(cls, inst_uuid: UUID, prop_uuid: UUID) -> None:
        c = mapper(InstanceFunctionLink).columns
        _ = Database.execute(
            sqla.delete(InstanceFunctionLink).where(
                c.inst_uuid == inst_uuid, c.prop_uuid == prop_uuid
            )
        )

    @classmethod
    @Database.use_same_session
    def delete_links_to_function(cls, function_uuid: UUID) -> None:
        c = mapper(InstanceFunctionLink).columns
        _ = Database.execute(
            sqla.delete(InstanceFunctionLink).where(c.function_uuid == function_uuid)
        )

    @classmethod
    @Database.use_same_session
    def function_links_of_instance(cls, inst_uuid: UUID) -> list[tuple[UUID, UUID]]:
        c = mapper(InstanceFunctionLink).columns
        rows = Database.execute(
            sqla.select(c.prop_uuid, c.function_uuid).where(c.inst_uuid == inst_uuid)
        ).all()
        return [(row[0], row[1]) for row in rows]

    @classmethod
    @Database.use_same_session
    def instance_uuids_bound_to(cls, function_uuid: UUID) -> list[UUID]:
        c = mapper(InstanceFunctionLink).columns
        rows = Database.execute(
            sqla.select(c.inst_uuid).where(c.function_uuid == function_uuid)
        ).all()
        return [row[0] for row in rows]


instance_function_links = InstanceFunctionLinks()
