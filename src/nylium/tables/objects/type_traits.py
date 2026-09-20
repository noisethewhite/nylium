"""The attach edges as a Mapping keyed by (type_uuid, trait_uuid).

The statement helpers used by the objects layer (ADR-0019) — attachment
lookups — live here as classmethods of ``TypeTraits``.
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.tables.objects.table_type_traits import TABLE_TypeTraits
from nylium.rows.objects.type_trait import TypeTrait


class TypeTraits(Table[tuple[UUID, UUID], TypeTrait]):
    """The attach edges as a Mapping keyed by (type_uuid, trait_uuid)."""

    __row__: ClassVar[type[Row]] = TypeTrait

    @Database.commit_after_this
    def attach(self, type_uuid: UUID, trait_uuid: UUID, position: int) -> TypeTrait:
        row = TABLE_TypeTraits(
            type_uuid=type_uuid, trait_uuid=trait_uuid, position=position
        )
        Database.add(row)
        Database.flush()
        return TypeTrait(row)

    @Database.commit_after_this
    def detach(self, type_uuid: UUID, trait_uuid: UUID) -> None:
        row = Database.get(TABLE_TypeTraits, (type_uuid, trait_uuid))
        if row is not None:
            Database.delete(row)

    @classmethod
    @Database.use_same_session
    def is_attached(cls, type_uuid: UUID, trait_uuid: UUID | None) -> bool:
        """True when (type_uuid, trait_uuid) is an attach edge (ADR-0019)."""
        if trait_uuid is None:
            return False
        attached = Database.scalar(
            sqla.select(TABLE_TypeTraits.type_uuid).where(
                TABLE_TypeTraits.type_uuid == type_uuid,
                TABLE_TypeTraits.trait_uuid == trait_uuid,
            )
        )
        return attached is not None

    @classmethod
    @Database.use_same_session
    def attached_trait_uuids(cls, type_uuid: UUID) -> list[UUID]:
        """Traits attached to the type, in attach order (ADR-0013/0019)."""
        return list(
            Database.scalars(
                sqla.select(TABLE_TypeTraits.trait_uuid)
                .where(TABLE_TypeTraits.type_uuid == type_uuid)
                .order_by(TABLE_TypeTraits.position)
            ).all()
        )


type_traits = TypeTraits()
