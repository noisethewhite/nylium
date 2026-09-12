# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""ADR-0014: decorative attributes (plural form, icon, color) live apart
from the entity tables, one decor row per entity row, 1:1 mandatory.

``type_decor`` decorates ``types`` (plural_name/icon/color);
``trait_decor`` decorates ``traits`` (color). The entity's ``create``
writes both rows in one commit; deletes cascade through the FK.
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.base import reg

__all__ = [
    "TABLE_TraitDecor",
    "TABLE_TypeDecor",
    "TraitDecor",
    "TypeDecor",
    "trait_decor",
    "type_decor",
]


@reg.mapped_as_dataclass
class TABLE_TypeDecor:
    """The decor row of one type. uuid is both PK and FK — 1:1 with types."""

    __tablename__: ClassVar[str] = "type_decor"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), primary_key=True
    )
    # plural display form; unique across types (moved from types in ADR-0014)
    plural_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # Material Symbols name or `img:<uuid>` (ADR-0006), rendered by the UI
    icon: Mapped[str] = mapped_column(
        Text, nullable=False, default="inventory_2", server_default="inventory_2"
    )
    # #RRGGBB hex; the default must match WColor.DEFAULT
    # (tables must not import objects — keep the literal in sync by hand)
    color: Mapped[str] = mapped_column(
        Text, nullable=False, default="#9e9e9e", server_default="#9e9e9e"
    )


@reg.mapped_as_dataclass
class TABLE_TraitDecor:
    """The decor row of one trait (ADR-0013 traits carry only a color)."""

    __tablename__: ClassVar[str] = "trait_decor"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("traits.uuid", ondelete="CASCADE"), primary_key=True
    )
    color: Mapped[str] = mapped_column(Text, nullable=False)


class TypeDecor(Row):
    """One type's decor: a writable snapshot of a TABLE_TypeDecor row."""

    __table__: ClassVar[type[object]] = TABLE_TypeDecor

    uuid: UUID
    plural_name: str
    icon: str
    color: str


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
        Database.session.add(row)
        Database.session.flush()
        return TypeDecor(row)


type_decor = TypeDecors()


class TraitDecor(Row):
    """One trait's decor: a writable snapshot of a TABLE_TraitDecor row."""

    __table__: ClassVar[type[object]] = TABLE_TraitDecor

    uuid: UUID
    color: str


class TraitDecors(Table[UUID, TraitDecor]):
    """The trait_decor table as a Mapping keyed by the trait's uuid."""

    __row__: ClassVar[type[Row]] = TraitDecor

    @databasemethod(commit=True)
    def create(self, uuid: UUID, color: str) -> TraitDecor:
        row = TABLE_TraitDecor(uuid=uuid, color=color)
        Database.session.add(row)
        Database.session.flush()
        return TraitDecor(row)


trait_decor = TraitDecors()
