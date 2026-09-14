"""The type_decor table as a Mapping keyed by the type's uuid."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

import sqlalchemy as sqla

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.decor.table_type_decor import TABLE_TypeDecor
from nylium.tables.decor.type_decor import TypeDecor


class TypeDecors(Table[UUID, TypeDecor]):
    """The type_decor table as a Mapping keyed by the type's uuid."""

    __row__: ClassVar[type[Row]] = TypeDecor

    @databasemethod(commit=True)
    def create(
        self, uuid: UUID, plural_name: str, icon: str | None, color: str | None
    ) -> TypeDecor:
        """None icon/color fall through to the column defaults — the
        defaults live in exactly one place (TABLE_TypeDecor)."""
        row = TABLE_TypeDecor(uuid=uuid, plural_name=plural_name)
        if icon is not None:
            row.icon = icon
        if color is not None:
            row.color = color
        Database.add(row)
        Database.flush()
        return TypeDecor(row)


@databasemethod(commit=False)
def reset_icons_referencing(icon_marker: str, default_glyph: str) -> None:
    """Every type whose icon equals ``icon_marker`` falls back to the default
    glyph (ADR-0006: an Image used as an icon may be deleted)."""
    for decor_row in Database.scalars(
        sqla.select(TABLE_TypeDecor).where(TABLE_TypeDecor.icon == icon_marker)
    ).all():
        decor_row.icon = default_glyph


type_decor = TypeDecors()
