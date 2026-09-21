"""The types table: Type (mapped Row) + Types (store) in one file (ADR-0033)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class Type(Row):
    """One type: identity + semantics (ADR-0014 keeps decor in type_decor).

    Cross-table navigation (props/traits/decor) lives in
    ``nylium.objects.navigation`` — a Row never imports a sibling table.
    """

    __tablename__: ClassVar[str] = "types"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(
        Text, nullable=False, default="object", server_default="object"
    )
    embedded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class Types(Table[UUID, Type]):
    """The types table as a Mapping of writable types."""

    __row__: ClassVar[type[Row]] = Type

    @Database.commit_after_this
    def create(
        self,
        name: str,
        plural_name: str,
        icon: str | None = None,
        kind: str | None = None,
        embedded: bool | None = None,
    ) -> Type:
        from nylium.table_rows.decor.type_decor import type_decor

        row = Type(name=name)
        if kind is not None:
            row.kind = kind
        if embedded is not None:
            row.embedded = embedded
        Database.add(row)
        Database.flush()
        _ = type_decor.create(row.uuid, plural_name, icon, None)
        return row

    @Database.commit_after_this
    def delete(self, uuid: UUID) -> None:
        row = Database.get(Type, uuid)
        if row is not None:
            Database.delete(row)  # its props cascade


types = Types()
