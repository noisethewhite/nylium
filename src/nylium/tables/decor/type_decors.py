"""TypeDecors table store for TypeDecor."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
import sqlalchemy as sqla
from nylium.database import Database
from nylium.database.row import mapper
from nylium.database.table import Row, Table
from nylium.rows.decor.type_decor import TypeDecor

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
