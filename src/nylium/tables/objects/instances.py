"""The instances table as a Mapping of writable instances (Table class + singleton).

The per-row statement helpers used by the objects layer (ADR-0019) — reads,
delete, modified_at bumps and ownership lookups — live here as classmethods
of ``Instances``. ``get`` is deliberately absent: ``instances.get(uuid)`` is
already ``Mapping.get`` (returns the ``Instance`` row or ``None``), so there
is nothing to re-home.
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.rows.objects.instance import Instance as Instance
from nylium.tables.objects.table_instances import TABLE_Instances as TABLE_Instances
from nylium.tables.objects.table_types import TABLE_Types


class Instances(Table[UUID, Instance]):
    """The instances table as a Mapping of writable instances."""

    __row__: ClassVar[type[Row]] = Instance

    @classmethod
    def _unique_plural_name(
        cls, uuid: UUID, name: str, plural_name: str | None = None
    ) -> str:
        """Pick a collision-free plural: "<name>s", or "<name>s-<uuid8>" if taken.

        Queries the live session, so rows pending in the current transaction
        (autoflush) count as taken too — matters when one transaction creates
        several same-named instances (nested arrays all named ``array``).
        """
        candidate = plural_name or f"{name}s"
        taken = (
            Database.query(TABLE_Instances.uuid)
            .filter_by(plural_name=candidate)
            .first()
        )
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
            TABLE_Instances(
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
        """Delete the instance row itself (caller handles value cleanup)."""
        row = Database.get(TABLE_Instances, uuid)
        if row is not None:
            Database.delete(row)

    @classmethod
    @Database.use_same_session
    def touch(cls, uuid: UUID) -> None:
        """Bump modified_at after any prop write."""
        _ = Database.execute(
            sqla.update(TABLE_Instances)
            .where(TABLE_Instances.uuid == uuid)
            .values(modified_at=sqla.func.now())
        )

    @classmethod
    @Database.use_same_session
    def owned_uuids(cls, owner_object_uuid: UUID) -> list[UUID]:
        """Uuids of every embedded instance owned by the given object."""
        return list(
            Database.scalars(
                sqla.select(TABLE_Instances.uuid).where(
                    TABLE_Instances.owner_object_uuid == owner_object_uuid
                )
            ).all()
        )

    @classmethod
    @Database.use_same_session
    def existing_uuids(cls, uuids: list[UUID]) -> set[UUID]:
        """The subset of ``uuids`` that are real instance rows (ADR-0019)."""
        if not uuids:
            return set()
        return set(
            Database.scalars(
                sqla.select(TABLE_Instances.uuid).where(
                    TABLE_Instances.uuid.in_(uuids)
                )
            ).all()
        )

    @classmethod
    @Database.use_same_session
    def uuids_of_kind(cls, kind: str) -> list[UUID]:
        """Uuids of every instance whose type has the given kind (ADR-0019)."""
        return list(
            Database.scalars(
                sqla.select(TABLE_Instances.uuid)
                .join(TABLE_Types, TABLE_Types.uuid == TABLE_Instances.type_uuid)
                .where(TABLE_Types.kind == kind)
            ).all()
        )


instances = Instances()
