"""Instances table store for Instance."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
import sqlalchemy as sqla
from nylium.database import Database
from nylium.database.row import mapper
from nylium.database.table import Row, Table
from nylium.data.rows.objects.instance import Instance

class Instances(Table[UUID, Instance]):
    """The instances table as a Mapping of writable instances."""

    __row__: ClassVar[type[Row]] = Instance

    @classmethod
    def _unique_plural_name(
        cls, uuid: UUID, name: str, plural_name: str | None = None
    ) -> str:
        c = mapper(Instance).columns
        candidate = plural_name or f"{name}s"
        taken = Database.scalar(sqla.select(c.uuid).where(c.plural_name == candidate))
        if taken is not None:
            candidate = f"{name}s-{str(uuid)[:8]}"
        return candidate

    @Database.commit_after_this
    def create(
        self,
        uuid: UUID,
        type_uuid: UUID,
        name: str,
        plural_name: str | None = None,
        owner_object_uuid: UUID | None = None,
        owner_prop_uuid: UUID | None = None,
    ) -> None:
        Database.add(
            Instance(
                uuid=uuid,
                type_uuid=type_uuid,
                name=name,
                plural_name=self._unique_plural_name(uuid, name, plural_name),
                owner_object_uuid=owner_object_uuid,
                owner_prop_uuid=owner_prop_uuid,
            )
        )
        Database.flush()

    @classmethod
    @Database.use_same_session
    def delete_row(cls, uuid: UUID) -> None:
        row = Database.get(Instance, uuid)
        if row is not None:
            Database.delete(row)

    @classmethod
    @Database.use_same_session
    def touch(cls, uuid: UUID) -> None:
        c = mapper(Instance).columns
        _ = Database.execute(
            sqla.update(Instance)
            .where(c.uuid == uuid)
            .values(modified_at=sqla.func.now())
        )

    @classmethod
    @Database.use_same_session
    def owned_uuids(cls, owner_object_uuid: UUID) -> list[UUID]:
        c = mapper(Instance).columns
        return list(
            Database.scalars(
                sqla.select(c.uuid).where(c.owner_object_uuid == owner_object_uuid)
            ).all()
        )

    @classmethod
    @Database.use_same_session
    def existing_uuids(cls, uuids: list[UUID]) -> set[UUID]:
        if not uuids:
            return set()
        c = mapper(Instance).columns
        return set(Database.scalars(sqla.select(c.uuid).where(c.uuid.in_(uuids))).all())

instances = Instances()
