"""The props table as a Mapping of writable props (Table class + singleton).

Also hosts the statement helpers used by the objects layer (ADR-0019):
lookups by owner, position rewrites, the full-draft schema sync and the
retype value purges (VALUE_TABLES).
"""
from __future__ import annotations

from typing import ClassVar, Protocol, TypeAlias
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import InstrumentedAttribute, Mapped

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.objects.prop import Prop as Prop
from nylium.tables.objects.table_props import TABLE_Props as TABLE_Props
from nylium.tables.values.boolean_values import TABLE_BooleanValues
from nylium.tables.values.date_values import TABLE_DateValues
from nylium.tables.values.datetime_values import TABLE_DatetimeValues
from nylium.tables.values.instance_values import TABLE_InstanceValues
from nylium.tables.values.integer_values import TABLE_IntegerValues
from nylium.tables.values.monthday_values import TABLE_MonthDayValues
from nylium.tables.values.monthdaytime_values import TABLE_MonthDayTimeValues
from nylium.tables.values.numeric_values import TABLE_NumericValues
from nylium.tables.values.string_values import TABLE_StringValues
from nylium.tables.values.time_values import TABLE_TimeValues

# (uuid | None, key, value_type_uuid | None, value_trait_uuid | None,
#  formula | None, collect | None) — None uuid means "new prop"; None formula
# / collect means a plain stored prop; value_type_uuid XOR value_trait_uuid
# (ADR-0013)
SchemaItem: TypeAlias = (
    "tuple[UUID | None, str, UUID | None, UUID | None, str | None, str | None]"
)


class _PropKeyedValues(Protocol):
    """Shape every per-prop value table shares (used for retype purge)."""

    inst_uuid: Mapped[UUID]
    prop_uuid: Mapped[UUID]


# Tables keyed by prop_uuid — a retype wipes the old values from all of
# them so the new type starts clean (Null) on every instance.
VALUE_TABLES: tuple[type[_PropKeyedValues], ...] = (
    TABLE_StringValues,
    TABLE_IntegerValues,
    TABLE_NumericValues,
    TABLE_BooleanValues,
    TABLE_DatetimeValues,
    TABLE_DateValues,
    TABLE_TimeValues,
    TABLE_MonthDayValues,
    TABLE_MonthDayTimeValues,
    TABLE_InstanceValues,
)


class Props(Table[UUID, Prop]):
    """The props table as a Mapping of writable props."""

    __row__: ClassVar[type[Row]] = Prop


props = Props()


@databasemethod(commit=False)
def by_type_key(owner_uuid: UUID, key: str) -> TABLE_Props | None:
    """One type-owned prop row by key (live ORM row — callers may write)."""
    return Database.scalar(
        sqla.select(TABLE_Props).where(
            TABLE_Props.owner_type_uuid == owner_uuid, TABLE_Props.key == key
        )
    )


@databasemethod(commit=False)
def by_trait_key(trait_uuid: UUID, key: str) -> TABLE_Props | None:
    """One trait-owned prop row by key (live ORM row — callers may write)."""
    return Database.scalar(
        sqla.select(TABLE_Props).where(
            TABLE_Props.owner_trait_uuid == trait_uuid, TABLE_Props.key == key
        )
    )


@databasemethod(commit=False)
def rows_of_type(owner_uuid: UUID) -> list[TABLE_Props]:
    """All props owned by the type, in schema order."""
    return list(
        Database.scalars(
            sqla.select(TABLE_Props)
            .where(TABLE_Props.owner_type_uuid == owner_uuid)
            .order_by(TABLE_Props.position)
        ).all()
    )


@databasemethod(commit=False)
def rows_of_trait(trait_uuid: UUID) -> list[TABLE_Props]:
    """All props owned by the trait, in schema order."""
    return list(
        Database.scalars(
            sqla.select(TABLE_Props)
            .where(TABLE_Props.owner_trait_uuid == trait_uuid)
            .order_by(TABLE_Props.position)
        ).all()
    )


@databasemethod(commit=False)
def apply_positions(owner_uuid: UUID, keys: list[str]) -> None:
    """Rewrite positions so the type's props render in `keys` order.
    `keys` must already be validated as a full-schema permutation."""
    rows = {row.key: row for row in rows_of_type(owner_uuid)}
    for position, key in enumerate(keys):
        rows[key].position = position
    Database.flush()


@databasemethod(commit=False)
def ensure_row(
    owner_uuid: UUID,
    key: str,
    value_type_uuid: UUID | None,
    value_trait_uuid: UUID | None,
    position: int,
    formula: str | None,
    collect: str | None,
) -> TABLE_Props:
    """Fetch-or-create one type-owned prop; an existing row is retyped /
    repositioned in place (flushed by the surrounding transaction)."""
    row = by_type_key(owner_uuid, key)
    if row is not None:
        row.value_type_uuid = value_type_uuid
        row.value_trait_uuid = value_trait_uuid
        row.position = position
        row.formula = formula
        row.collect = collect
        return row
    row = TABLE_Props(
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


@databasemethod(commit=False)
def sync_owned(
    owner_column: InstrumentedAttribute[UUID | None],
    owner_column_name: str,
    owner_uuid: UUID,
    items: list[SchemaItem],
) -> None:
    """Apply a full schema draft against one owner column
    (owner_type_uuid or owner_trait_uuid): rows whose uuid matches an
    existing prop are renamed/retyped/repositioned in place, uuid-less
    rows are created, props missing from the draft are deleted (their
    values cascade). A changed value type purges the prop's values.
    Deletes flush first so a freed key can be reused by a new prop in
    the same sync."""
    existing = {
        row.uuid: row
        for row in Database.scalars(
            sqla.select(TABLE_Props).where(owner_column == owner_uuid)
        )
    }
    kept = {uuid for uuid, _, _, _, _, _ in items if uuid is not None}
    for stale_uuid, stale_row in existing.items():
        if stale_uuid not in kept:
            Database.delete(stale_row)
    Database.flush()
    for position, (
        prop_uuid, key, value_type_uuid, value_trait_uuid, formula, collect
    ) in enumerate(items):
        if prop_uuid is None or prop_uuid not in existing:
            row = TABLE_Props(
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
            purge_values(prop_uuid)
            row.value_type_uuid = value_type_uuid
            row.value_trait_uuid = value_trait_uuid
        row.key = key
        row.position = position
        row.formula = formula
        row.collect = collect
    Database.flush()


@databasemethod(commit=False)
def purge_values(prop_uuid: UUID) -> None:
    """Wipe the prop's values from every prop-keyed table (retype)."""
    for table in VALUE_TABLES:
        _ = Database.execute(
            sqla.delete(table).where(table.prop_uuid == prop_uuid)
        )
    Database.flush()


@databasemethod(commit=False)
def purge_values_for_instances(prop_uuid: UUID, inst_uuids: list[UUID]) -> None:
    """Wipe this prop's values, but only on the given instances (ADR-0013
    detach: the trait's other types keep theirs)."""
    if not inst_uuids:
        return
    for table in VALUE_TABLES:
        _ = Database.execute(
            sqla.delete(table).where(
                table.prop_uuid == prop_uuid,
                table.inst_uuid.in_(inst_uuids),
            )
        )
    Database.flush()
