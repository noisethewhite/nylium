"""The type_traits attach edges: TypeTrait (mapped Row) + TypeTraits (store)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.row import mapper
from nylium.database.table import Row, Table
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TypeTrait(Row):
    __tablename__: ClassVar[str] = "type_traits"

    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), primary_key=True
    )
    trait_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("traits.uuid", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class TypeTraits(Table[tuple[UUID, UUID], TypeTrait]):
    """The attach edges as a Mapping keyed by (type_uuid, trait_uuid)."""

    __row__: ClassVar[type[Row]] = TypeTrait

    @Database.commit_after_this
    def attach(self, type_uuid: UUID, trait_uuid: UUID, position: int) -> TypeTrait:
        row = TypeTrait(type_uuid=type_uuid, trait_uuid=trait_uuid, position=position)
        Database.add(row)
        Database.flush()
        return row

    @Database.commit_after_this
    def detach(self, type_uuid: UUID, trait_uuid: UUID) -> None:
        row = Database.get(TypeTrait, (type_uuid, trait_uuid))
        if row is not None:
            Database.delete(row)

    @classmethod
    @Database.use_same_session
    def is_attached(cls, type_uuid: UUID, trait_uuid: UUID | None) -> bool:
        if trait_uuid is None:
            return False
        c = mapper(TypeTrait).columns
        attached = Database.scalar(
            sqla.select(c.type_uuid).where(
                c.type_uuid == type_uuid, c.trait_uuid == trait_uuid
            )
        )
        return attached is not None

    @classmethod
    @Database.use_same_session
    def attached_trait_uuids(cls, type_uuid: UUID) -> list[UUID]:
        c = mapper(TypeTrait).columns
        return list(
            Database.scalars(
                sqla.select(c.trait_uuid)
                .where(c.type_uuid == type_uuid)
                .order_by(c.position)
            ).all()
        )


type_traits = TypeTraits()
