"""WProp: handle on a row of the `props` table.

Owns every query against `props` — WType deliberately does not import
WProp, so the dependency direction is wprop -> wtype and nothing cycles.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Protocol, TypeAlias
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Mapped, Session

from nylium.database import (
    BooleanValues,
    Database,
    DatetimeValues,
    DateValues,
    InstanceValues,
    IntegerValues,
    MonthDayTimeValues,
    MonthDayValues,
    NumericValues,
    Props,
    StringValues,
    TimeValues,
)

if TYPE_CHECKING:
    from nylium.objects.wtype import WType

# (uuid | None, key, value_type_uuid) — None uuid means "new prop"
SchemaItem: TypeAlias = "tuple[UUID | None, str, UUID]"


class _PropKeyedValues(Protocol):
    """Shape every per-prop value table shares (used for retype purge)."""

    prop_uuid: Mapped[UUID]


# Tables keyed by prop_uuid — a retype wipes the old values from all of
# them so the new type starts clean (Null) on every instance.
VALUE_TABLES: tuple[type[_PropKeyedValues], ...] = (
    StringValues,
    IntegerValues,
    NumericValues,
    BooleanValues,
    DatetimeValues,
    DateValues,
    TimeValues,
    MonthDayValues,
    MonthDayTimeValues,
    InstanceValues,
)


class WProp:
    ROW: ClassVar[type[Props]] = Props

    _row: Props

    def __init__(self, row: Props):
        # snapshot for reads (session-independent); _row is kept only for
        # the write path in ensure() and is guarded there
        self._row = row
        self._uuid: UUID = row.uuid
        self._key: str = row.key
        self._value_type_uuid: UUID = row.value_type_uuid

    @property
    def uuid(self) -> UUID:
        return self._uuid

    @property
    def key(self) -> str:
        return self._key

    def _live_row(self) -> Props:
        if sqla.inspect(self._row).detached:
            msg = f"prop {self._key!r} wraps a row whose session is gone — writes must run inside a sessionmethod chain"
            raise RuntimeError(msg)
        return self._row

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_key(cls, session: Session, owner: "WType", key: str) -> "WProp | None":
        row = session.scalar(
            sqla.select(Props).where(
                Props.owner_type_uuid == owner.uuid, Props.key == key
            )
        )
        return None if row is None else cls(row)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def all_for(cls, session: Session, owner: "WType") -> "list[WProp]":
        rows = session.scalars(
            sqla.select(Props)
            .where(Props.owner_type_uuid == owner.uuid)
            .order_by(Props.position)
        ).all()
        return [cls(row) for row in rows]

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def reorder(cls, session: Session, owner: "WType", keys: list[str]) -> None:
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
        session.flush()

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def sync_schema(
        cls, session: Session, owner: "WType", items: list[SchemaItem]
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
            for row in session.scalars(
                sqla.select(Props).where(Props.owner_type_uuid == owner.uuid)
            )
        }
        kept = {uuid for uuid, _, _ in items if uuid is not None}
        for stale_uuid, stale_row in existing.items():
            if stale_uuid not in kept:
                session.delete(stale_row)
        session.flush()
        for position, (prop_uuid, key, value_type_uuid) in enumerate(items):
            if prop_uuid is None or prop_uuid not in existing:
                session.add(
                    Props(
                        uuid=uuid4(),
                        key=key,
                        owner_type_uuid=owner.uuid,
                        value_type_uuid=value_type_uuid,
                        position=position,
                    )
                )
                continue
            row = existing[prop_uuid]
            if row.value_type_uuid != value_type_uuid:
                cls._purge_values(session, prop_uuid)
                row.value_type_uuid = value_type_uuid
            row.key = key
            row.position = position
        session.flush()

    @classmethod
    def _purge_values(cls, session: Session, prop_uuid: UUID) -> None:
        for table in VALUE_TABLES:
            _ = session.execute(
                sqla.delete(table).where(table.prop_uuid == prop_uuid)
            )
        session.flush()

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def ensure(
        cls, session: Session, owner: "WType", key: str, value_type: "WType",
        position: int = 0,
    ) -> "WProp":
        existing = cls.by_key(owner, key)
        if existing is not None:
            live = existing._live_row()
            live.value_type_uuid = value_type.uuid
            live.position = position
            return existing
        row = Props(
            uuid=uuid4(),
            key=key,
            owner_type_uuid=owner.uuid,
            value_type_uuid=value_type.uuid,
            position=position,
        )
        session.add(row)
        session.flush()
        return cls(row)

    @Database.sessionmethod(bundled=True, commit=False)
    def value_type(self) -> "WType":
        from nylium.objects.wtype import WType

        value_type = WType.by_uuid(self._value_type_uuid)
        if value_type is None:
            raise RuntimeError(f"prop {self.key!r} has dangling value type")
        return value_type
