"""The instances table as a Mapping of writable instances (Table class + singleton)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.objects.instance import Instance as Instance
from nylium.tables.objects.table_instances import TABLE_Instances as TABLE_Instances


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


class Instances(Table[UUID, Instance]):
    """The instances table as a Mapping of writable instances."""

    __row__: ClassVar[type[Row]] = Instance

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
