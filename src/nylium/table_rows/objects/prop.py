"""The props table: Prop (mapped Row) + Props (store) in one file (ADR-0033)."""
from __future__ import annotations

from typing import ClassVar, TypeAlias
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.row import mapper
from nylium.database.table import Row, Table
from nylium.tables.base import reg

SchemaItem: TypeAlias = (
    "tuple[UUID | None, str, UUID | None, UUID | None, str | None, str | None]"
)


@reg.mapped_as_dataclass
class Prop(Row):
    __tablename__: ClassVar[str] = "props"
    __table_args__: ClassVar[tuple[object, ...]] = (
        UniqueConstraint("owner_type_uuid", "key"),
        UniqueConstraint("owner_trait_uuid", "key"),
        CheckConstraint(
            "(owner_type_uuid IS NULL) <> (owner_trait_uuid IS NULL)",
            name="props_owner_exactly_one",
        ),
        CheckConstraint(
            "(value_type_uuid IS NULL) <> (value_trait_uuid IS NULL)",
            name="props_value_exactly_one",
        ),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    owner_type_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=True, default=None
    )
    owner_trait_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("traits.uuid", ondelete="CASCADE"), nullable=True, default=None
    )
    value_type_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("types.uuid"), nullable=True, default=None
    )
    value_trait_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("traits.uuid", ondelete="RESTRICT"), nullable=True, default=None
    )
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    formula: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    collect: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)


class Props(Table[UUID, Prop]):
    """The props table as a Mapping of writable props.

    Cross-table concerns (value purge on retype, owner/value navigation)
    live in ``nylium.objects.navigation`` — a table store never imports a
    sibling table (ADR-0033).
    """

    __row__: ClassVar[type[Row]] = Prop

    @classmethod
    @Database.use_same_session
    def by_type_key(cls, owner_uuid: UUID, key: str) -> Prop | None:
        c = mapper(Prop).columns
        return Database.scalar(
            sqla.select(Prop).where(c.owner_type_uuid == owner_uuid, c.key == key)
        )

    @classmethod
    @Database.use_same_session
    def by_trait_key(cls, trait_uuid: UUID, key: str) -> Prop | None:
        c = mapper(Prop).columns
        return Database.scalar(
            sqla.select(Prop).where(c.owner_trait_uuid == trait_uuid, c.key == key)
        )

    @classmethod
    @Database.use_same_session
    def rows_of_type(cls, owner_uuid: UUID) -> list[Prop]:
        c = mapper(Prop).columns
        return list(
            Database.scalars(
                sqla.select(Prop)
                .where(c.owner_type_uuid == owner_uuid)
                .order_by(c.position)
            ).all()
        )

    @classmethod
    @Database.use_same_session
    def rows_of_trait(cls, trait_uuid: UUID) -> list[Prop]:
        c = mapper(Prop).columns
        return list(
            Database.scalars(
                sqla.select(Prop)
                .where(c.owner_trait_uuid == trait_uuid)
                .order_by(c.position)
            ).all()
        )

    @classmethod
    @Database.use_same_session
    def apply_positions(cls, owner_uuid: UUID, keys: list[str]) -> None:
        rows = {row.key: row for row in cls.rows_of_type(owner_uuid)}
        for position, key in enumerate(keys):
            rows[key].position = position
        Database.flush()

    @classmethod
    @Database.use_same_session
    def ensure_row(
        cls,
        owner_uuid: UUID,
        key: str,
        value_type_uuid: UUID | None,
        value_trait_uuid: UUID | None,
        position: int,
        formula: str | None,
        collect: str | None,
    ) -> Prop:
        row = cls.by_type_key(owner_uuid, key)
        if row is not None:
            row.value_type_uuid = value_type_uuid
            row.value_trait_uuid = value_trait_uuid
            row.position = position
            row.formula = formula
            row.collect = collect
            return row
        row = Prop(
            uuid=uuid4(),
            key=key,
            owner_type_uuid=owner_uuid,
            value_type_uuid=value_type_uuid,
            value_trait_uuid=value_trait_uuid,
            position=position,
            formula=formula,
            collect=collect,
        )
        Database.add(row)
        Database.flush()
        return row

    @classmethod
    @Database.use_same_session
    def sync_owned(
        cls,
        owner_column: sqla.ColumnElement[object],
        owner_column_name: str,
        owner_uuid: UUID,
        items: list[SchemaItem],
    ) -> list[UUID]:
        """Apply a full schema draft against one owner column (see ADR-0019).

        Returns the uuids of props whose value typing changed — the caller
        purges their stored values via
        ``nylium.objects.navigation.purge_prop_values``, so this module
        never imports the value tables.
        """
        existing = {
            row.uuid: row
            for row in Database.scalars(
                sqla.select(Prop).where(owner_column == owner_uuid)
            )
        }
        kept = {uuid for uuid, _, _, _, _, _ in items if uuid is not None}
        for stale_uuid, stale_row in existing.items():
            if stale_uuid not in kept:
                Database.delete(stale_row)
        Database.flush()
        retyped: list[UUID] = []
        for position, (
            prop_uuid, key, value_type_uuid, value_trait_uuid, formula, collect
        ) in enumerate(items):
            if prop_uuid is None or prop_uuid not in existing:
                row = Prop(
                    uuid=uuid4(),
                    key=key,
                    value_type_uuid=value_type_uuid,
                    value_trait_uuid=value_trait_uuid,
                    position=position,
                    formula=formula,
                    collect=collect,
                )
                setattr(row, owner_column_name, owner_uuid)
                Database.add(row)
                continue
            row = existing[prop_uuid]
            if (
                row.value_type_uuid != value_type_uuid
                or row.value_trait_uuid != value_trait_uuid
            ):
                retyped.append(prop_uuid)
                row.value_type_uuid = value_type_uuid
                row.value_trait_uuid = value_trait_uuid
            row.key = key
            row.position = position
            row.formula = formula
            row.collect = collect
        Database.flush()
        return retyped


props = Props()
