"""InstanceLinks table store for InstanceLink."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
import sqlalchemy as sqla
from nylium.database import Database
from nylium.database.Row import Row, get_mapper
from nylium.database.Table import Table
from nylium.data.rows import InstanceLink

class InstanceLinks(Table[tuple[UUID, UUID], InstanceLink]):
    """The instance_links table as a store of link rows."""

    __row__: ClassVar[type[Row]] = InstanceLink

    @classmethod
    @Database.use_same_session
    def link_for(cls, inst_uuid: UUID, prop_uuid: UUID) -> InstanceLink | None:
        """The link row held by (owner instance, prop), or None."""
        c = get_mapper(InstanceLink).columns
        return Database.scalar(
            sqla.select(InstanceLink).where(
                c.inst_uuid == inst_uuid, c.prop_uuid == prop_uuid
            )
        )

    @classmethod
    @Database.use_same_session
    def merge_link(cls, uuid: UUID, prop_uuid: UUID, inst_uuid: UUID) -> None:
        """Insert-or-replace the link row for (owner, prop) — the composite
        pk — pointing at the given target uuid (ADR-0028)."""
        _ = Database.merge(
            InstanceLink(uuid=uuid, prop_uuid=prop_uuid, inst_uuid=inst_uuid)
        )

    @classmethod
    @Database.use_same_session
    def delete_row(cls, row: InstanceLink) -> None:
        """Delete the given link row (already fetched by the caller)."""
        Database.delete(row)

    @classmethod
    @Database.use_same_session
    def delete_links_to(cls, uuid: UUID) -> None:
        """Delete every link row whose target is the given instance uuid."""
        c = get_mapper(InstanceLink).columns
        _ = Database.execute(sqla.delete(InstanceLink).where(c.uuid == uuid))

    @classmethod
    @Database.use_same_session
    def linked_uuids_of(cls, prop_uuid: UUID) -> list[UUID]:
        """Uuids of every instance linked through the given prop, across all
        owners — the sweep list before an embedded prop is deleted or retyped."""
        c = get_mapper(InstanceLink).columns
        return list(
            Database.scalars(sqla.select(c.uuid).where(c.prop_uuid == prop_uuid)).all()
        )

    @classmethod
    @Database.use_same_session
    def add_link(cls, uuid: UUID, prop_uuid: UUID, inst_uuid: UUID) -> None:
        """Insert a brand-new link row and flush — the embedded child is a fresh
        uuid4, so this must stay a plain insert (merge would mask a uuid
        collision instead of failing on it). The flush pins insert order:
        instance_links.uuid FKs into instances."""
        Database.add(InstanceLink(uuid=uuid, prop_uuid=prop_uuid, inst_uuid=inst_uuid))
        Database.flush()

instance_links = InstanceLinks()
