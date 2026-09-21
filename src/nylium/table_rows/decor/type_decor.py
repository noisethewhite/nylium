"""The type_decor table: TypeDecor (mapped Row) + TypeDecors (store)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.row import mapper
from nylium.database.table import Row, Table
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class TypeDecor(Row):
    __tablename__: ClassVar[str] = "type_decor"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), primary_key=True
    )
    plural_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    icon: Mapped[str] = mapped_column(
        Text, nullable=False, default="inventory_2", server_default="inventory_2"
    )
    color: Mapped[str] = mapped_column(
        Text, nullable=False, default="#9e9e9e", server_default="#9e9e9e"
    )


class TypeDecors(Table[UUID, TypeDecor]):
    """The type_decor table as a Mapping keyed by the type's uuid."""

    __row__: ClassVar[type[Row]] = TypeDecor

    @Database.commit_after_this
    def create(
        self, uuid: UUID, plural_name: str, icon: str | None, color: str | None
    ) -> TypeDecor:
        row = TypeDecor(uuid=uuid, plural_name=plural_name)
        if icon is not None:
            row.icon = icon
        if color is not None:
            row.color = color
        Database.add(row)
        Database.flush()
        return row

    @classmethod
    @Database.use_same_session
    def reset_icons_referencing(cls, icon_marker: str, default_glyph: str) -> None:
        c = mapper(TypeDecor).columns
        for decor_row in Database.scalars(
            sqla.select(TypeDecor).where(c.icon == icon_marker)
        ).all():
            decor_row.icon = default_glyph


type_decor = TypeDecors()
