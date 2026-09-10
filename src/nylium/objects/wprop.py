"""WProp: handle on a row of the `props` table.

Owns every query against `props` — WType deliberately does not import
WProp, so the dependency direction is wprop -> wtype and nothing cycles.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Protocol, TypeAlias
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import InstanceState, Mapped

from nylium.database import Database, databasemethod
from nylium.tables import (
    TABLE_BooleanValues,
    TABLE_DatetimeValues,
    TABLE_DateValues,
    TABLE_InstanceValues,
    TABLE_IntegerValues,
    TABLE_MonthDayTimeValues,
    TABLE_MonthDayValues,
    TABLE_NumericValues,
    TABLE_Props,
    TABLE_StringValues,
    TABLE_TimeValues,
)

if TYPE_CHECKING:
    from nylium.objects.wtype import WType

# (uuid | None, key, value_type_uuid, formula | None) — None uuid means
# "new prop"; None formula means a plain stored prop
SchemaItem: TypeAlias = "tuple[UUID | None, str, UUID, str | None]"


class _PropKeyedValues(Protocol):
    """Shape every per-prop value table shares (used for retype purge)."""

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


class WProp:
    ROW: ClassVar[type[TABLE_Props]] = TABLE_Props

    _row: TABLE_Props

    def __init__(self, row: TABLE_Props):
        # snapshot for reads (session-independent); _row is kept only for
        # the write path in ensure() and is guarded there
        self._row = row
        self._uuid: UUID = row.uuid
        self._key: str = row.key
        self._value_type_uuid: UUID = row.value_type_uuid
        self._formula: str | None = row.formula
        self._function_uuid: UUID | None = row.function_uuid

    @property
    def uuid(self) -> UUID:
        return self._uuid

    @property
    def key(self) -> str:
        return self._key

    @property
    def formula(self) -> str | None:
        return self._formula

    @property
    def function_uuid(self) -> UUID | None:
        return self._function_uuid

    def _live_row(self) -> TABLE_Props:
        state = sqla.inspect(self._row)
        assert isinstance(state, InstanceState)
        if state.detached:
            msg = f"prop {self._key!r} wraps a row whose session is gone — writes must run inside a sessionmethod chain"
            raise RuntimeError(msg)
        return self._row

    @classmethod
    @databasemethod(commit=False)
    def by_key(cls, owner: "WType", key: str) -> "WProp | None":
        row = Database.session.scalar(
            sqla.select(TABLE_Props).where(
                TABLE_Props.owner_type_uuid == owner.uuid, TABLE_Props.key == key
            )
        )
        return None if row is None else cls(row)

    @classmethod
    @databasemethod(commit=False)
    def all_for(cls, owner: "WType") -> "list[WProp]":
        rows = Database.session.scalars(
            sqla.select(TABLE_Props)
            .where(TABLE_Props.owner_type_uuid == owner.uuid)
            .order_by(TABLE_Props.position)
        ).all()
        return [cls(row) for row in rows]

    @classmethod
    @databasemethod(commit=True)
    def reorder(cls, owner: "WType", keys: list[str]) -> None:
        """Rewrite positions so props render in `keys` order. The list
        must be a permutation of the whole schema — partial orders would
        silently orphan the props left out."""
        props = {prop.key: prop._live_row() for prop in cls.all_for(owner)}
        if set(keys) != set(props):
            raise ValueError(
                f"prop order {keys!r} does not match {owner.name!r} schema"
            )
        for position, key in enumerate(keys):
            props[key].position = position
        Database.session.flush()

    @classmethod
    @databasemethod(commit=True)
    def sync_schema(
        cls, owner: "WType", items: list[SchemaItem]
    ) -> None:
        """Apply the editor's full draft: rows whose uuid matches an
        existing prop are renamed/retyped/repositioned in place, uuid-less
        rows are created, props missing from the draft are deleted (their
        values cascade). A changed value type purges the prop's values —
        old data rarely survives a type change, so every instance reads
        Null again. Deletes flush first so a freed key can be reused by a
        new prop in the same sync."""
        existing = {
            row.uuid: row
            for row in Database.session.scalars(
                sqla.select(TABLE_Props).where(TABLE_Props.owner_type_uuid == owner.uuid)
            )
        }
        kept = {uuid for uuid, _, _, _ in items if uuid is not None}
        for stale_uuid, stale_row in existing.items():
            if stale_uuid not in kept:
                Database.session.delete(stale_row)
        Database.session.flush()
        for position, (prop_uuid, key, value_type_uuid, formula) in enumerate(items):
            if prop_uuid is None or prop_uuid not in existing:
                Database.session.add(
                    TABLE_Props(
                        uuid=uuid4(),
                        key=key,
                        owner_type_uuid=owner.uuid,
                        value_type_uuid=value_type_uuid,
                        position=position,
                        formula=formula,
                    )
                )
                continue
            row = existing[prop_uuid]
            if row.value_type_uuid != value_type_uuid:
                cls._purge_values(prop_uuid)
                row.value_type_uuid = value_type_uuid
            row.key = key
            row.position = position
            row.formula = formula
        Database.session.flush()

    @classmethod
    def _purge_values(cls, prop_uuid: UUID) -> None:
        for table in VALUE_TABLES:
            _ = Database.session.execute(
                sqla.delete(table).where(table.prop_uuid == prop_uuid)
            )
        Database.session.flush()

    @classmethod
    @databasemethod(commit=True)
    def ensure(
        cls, owner: "WType", key: str, value_type: "WType",
        position: int = 0, formula: str | None = None,
    ) -> "WProp":
        existing = cls.by_key(owner, key)
        if existing is not None:
            live = existing._live_row()
            live.value_type_uuid = value_type.uuid
            live.position = position
            live.formula = formula
            return existing
        row = TABLE_Props(
            uuid=uuid4(),
            key=key,
            owner_type_uuid=owner.uuid,
            value_type_uuid=value_type.uuid,
            position=position,
            formula=formula,
        )
        Database.session.add(row)
        Database.session.flush()
        return cls(row)

    @databasemethod(commit=False)
    def value_type(self) -> "WType":
        from nylium.objects.wtype import WType

        value_type = WType.by_uuid(self._value_type_uuid)
        if value_type is None:
            raise RuntimeError(f"prop {self.key!r} has dangling value type")
        return value_type
