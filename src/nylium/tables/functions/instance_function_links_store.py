"""Instance function links store — the function-binding statements
(ADR-0029 / ADR-0019, ADR-0031).

Moved verbatim from ``objects/wfunction/function_links.py`` (ADR-0030
phase C); only the import paths change. The ``TABLE_InstanceFunctionLinks``
class stays in ``tables/functions/instance_function_links.py``.
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.rows.functions.instance_function_link import InstanceFunctionLink
from nylium.tables.functions.instance_function_links import TABLE_InstanceFunctionLinks


class InstanceFunctionLinks(Table[tuple[UUID, UUID], InstanceFunctionLink]):
    """The instance_function_links table as a store of function bindings."""

    __row__: ClassVar[type[Row]] = InstanceFunctionLink

    @classmethod
    @Database.use_same_session
    def function_link_for(
        cls, inst_uuid: UUID, prop_uuid: UUID
    ) -> TABLE_InstanceFunctionLinks | None:
        """The function bound to (owner instance, prop), or None."""
        return Database.scalar(
            sqla.select(TABLE_InstanceFunctionLinks).where(
                TABLE_InstanceFunctionLinks.inst_uuid == inst_uuid,
                TABLE_InstanceFunctionLinks.prop_uuid == prop_uuid,
            )
        )

    @classmethod
    @Database.use_same_session
    def function_uuid_for(cls, inst_uuid: UUID, prop_uuid: UUID) -> UUID | None:
        """The uuid of the function bound to (owner instance, prop), or None."""
        row = cls.function_link_for(inst_uuid, prop_uuid)
        return None if row is None else row.function_uuid

    @classmethod
    @Database.use_same_session
    def merge_function_link(
        cls, inst_uuid: UUID, prop_uuid: UUID, function_uuid: UUID
    ) -> None:
        """Insert-or-replace the (owner, prop) -> function binding."""
        _ = Database.merge(
            TABLE_InstanceFunctionLinks(
                inst_uuid=inst_uuid, prop_uuid=prop_uuid, function_uuid=function_uuid
            )
        )

    @classmethod
    @Database.use_same_session
    def delete_function_link(cls, inst_uuid: UUID, prop_uuid: UUID) -> None:
        """Remove the (owner, prop) -> function binding, if any."""
        _ = Database.execute(
            sqla.delete(TABLE_InstanceFunctionLinks).where(
                TABLE_InstanceFunctionLinks.inst_uuid == inst_uuid,
                TABLE_InstanceFunctionLinks.prop_uuid == prop_uuid,
            )
        )

    @classmethod
    @Database.use_same_session
    def delete_links_to_function(cls, function_uuid: UUID) -> None:
        """Drop every binding pointing at the given function (on delete)."""
        _ = Database.execute(
            sqla.delete(TABLE_InstanceFunctionLinks).where(
                TABLE_InstanceFunctionLinks.function_uuid == function_uuid
            )
        )

    @classmethod
    @Database.use_same_session
    def function_links_of_instance(cls, inst_uuid: UUID) -> list[tuple[UUID, UUID]]:
        """(prop_uuid, function_uuid) pairs bound on the given instance."""
        rows = Database.execute(
            sqla.select(
                TABLE_InstanceFunctionLinks.prop_uuid,
                TABLE_InstanceFunctionLinks.function_uuid,
            ).where(TABLE_InstanceFunctionLinks.inst_uuid == inst_uuid)
        ).all()
        return [(row[0], row[1]) for row in rows]

    @classmethod
    @Database.use_same_session
    def instance_uuids_bound_to(cls, function_uuid: UUID) -> list[UUID]:
        """Every owner instance that binds the given function (for re-running
        the local cycle check after a function's DAG changes)."""
        rows = Database.execute(
            sqla.select(TABLE_InstanceFunctionLinks.inst_uuid).where(
                TABLE_InstanceFunctionLinks.function_uuid == function_uuid
            )
        ).all()
        return [row[0] for row in rows]


instance_function_links = InstanceFunctionLinks()
