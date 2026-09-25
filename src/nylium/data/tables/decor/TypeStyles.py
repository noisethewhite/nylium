"""TypeStyles table store for TypeStyle."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID
import sqlalchemy as sqla
from nylium.database import Database
from nylium.database.Row import get_mapper
from nylium.database.Table import Row, Table
from nylium.data.rows import TypeStyle

class TypeStyles(Table[UUID, TypeStyle]):
    """The type_style table as a Mapping keyed by the type's uuid."""

    __row__: ClassVar[type[Row]] = TypeStyle

    @Database.commit_after_this
    def create(
        self, uuid: UUID, plural_name: str, icon: str | None, color: str | None
    ) -> TypeStyle:
        row = TypeStyle(uuid=uuid, plural_name=plural_name)
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
        c = get_mapper(TypeStyle).columns
        for decor_row in Database.scalars(
            sqla.select(TypeStyle).where(c.icon == icon_marker)
        ).all():
            decor_row.icon = default_glyph

type_style = TypeStyles()
