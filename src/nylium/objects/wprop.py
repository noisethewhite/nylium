"""WProp: handle on a row of the `props` table.

Owns every query against `props` — WType deliberately does not import
WProp, so the dependency direction is wprop -> wtype and nothing cycles.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Protocol, TypeAlias
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import InstanceState, InstrumentedAttribute, Mapped

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
    TABLE_Traits,
    TABLE_TypeTraits,
)

if TYPE_CHECKING:
    from nylium.objects.wtype import WType

# (uuid | None, key, value_type_uuid | None, value_trait_uuid | None,
#  formula | None) — None uuid means "new prop"; None formula means a
# plain stored prop; value_type_uuid XOR value_trait_uuid (ADR-0013)
SchemaItem: TypeAlias = "tuple[UUID | None, str, UUID | None, UUID | None, str | None]"


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


class WProp:
    ROW: ClassVar[type[TABLE_Props]] = TABLE_Props

    _row: TABLE_Props

    def __init__(self, row: TABLE_Props):
        # snapshot for reads (session-independent); _row is kept only for
        # the write path in ensure() and is guarded there
        self._row = row
        self._uuid: UUID = row.uuid
        self._key: str = row.key
        self._value_type_uuid: UUID | None = row.value_type_uuid
        self._value_trait_uuid: UUID | None = row.value_trait_uuid
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

    @property
    def is_trait_bound(self) -> bool:
        """ADR-0013: the prop's value is 'any object with trait X', not one
        concrete type."""
        return self._value_trait_uuid is not None

    @databasemethod(commit=False)
    def value_trait_name(self) -> str:
        """The bound trait's name — only valid on trait-bound props."""
        if self._value_trait_uuid is None:
            raise RuntimeError(f"prop {self.key!r} is not trait-bound")
        row = Database.session.get(TABLE_Traits, self._value_trait_uuid)
        if row is None:
            raise RuntimeError(f"prop {self.key!r} has a dangling value trait")
        return str(row.name)

    @databasemethod(commit=False)
    def value_spec_name(self) -> str:
        """The wire-facing value spec: concrete type name, or
        ``Any<TraitName>`` for a trait-bound prop (ADR-0013)."""
        if self.is_trait_bound:
            return f"Any<{self.value_trait_name()}>"
        return self.value_type().name

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
        cls._sync(TABLE_Props.owner_type_uuid, "owner_type_uuid", owner.uuid, items)

    @classmethod
    @databasemethod(commit=True)
    def sync_trait_schema(cls, trait_uuid: UUID, items: list[SchemaItem]) -> None:
        """Same full-draft semantics as sync_schema, but the owner is a
        trait (ADR-0013). Retype purges values exactly like type-owned
        props."""
        cls._sync(TABLE_Props.owner_trait_uuid, "owner_trait_uuid", trait_uuid, items)

    @classmethod
    def _sync(
        cls,
        owner_column: InstrumentedAttribute[UUID | None],
        owner_column_name: str,
        owner_uuid: UUID,
        items: list[SchemaItem],
    ) -> None:
        existing = {
            row.uuid: row
            for row in Database.session.scalars(
                sqla.select(TABLE_Props).where(
                    owner_column == owner_uuid
                )
            )
        }
        kept = {uuid for uuid, _, _, _, _ in items if uuid is not None}
        for stale_uuid, stale_row in existing.items():
            if stale_uuid not in kept:
                Database.session.delete(stale_row)
        Database.session.flush()
        for position, (prop_uuid, key, value_type_uuid, value_trait_uuid, formula) in enumerate(
            items
        ):
            if prop_uuid is None or prop_uuid not in existing:
                row = TABLE_Props(
                    uuid=uuid4(),
                    key=key,
                    value_type_uuid=value_type_uuid,
                    value_trait_uuid=value_trait_uuid,
                    position=position,
                    formula=formula,
                )
                setattr(row, owner_column_name, owner_uuid)
                Database.session.add(row)
                continue
            row = existing[prop_uuid]
            if (
                row.value_type_uuid != value_type_uuid
                or row.value_trait_uuid != value_trait_uuid
            ):
                cls._purge_values(prop_uuid)
                row.value_type_uuid = value_type_uuid
                row.value_trait_uuid = value_trait_uuid
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
    def purge_values_for_instances(cls, prop_uuid: UUID, inst_uuids: list[UUID]) -> None:
        """ADR-0013 detach: wipe this prop's values, but only on the given
        instances (the trait's other types keep theirs)."""
        if not inst_uuids:
            return
        for table in VALUE_TABLES:
            _ = Database.session.execute(
                sqla.delete(table).where(
                    table.prop_uuid == prop_uuid,
                    table.inst_uuid.in_(inst_uuids),
                )
            )
        Database.session.flush()

    @classmethod
    @databasemethod(commit=True)
    def ensure(
        cls, owner: "WType", key: str, value_type: "WType | None",
        position: int = 0, formula: str | None = None,
        value_trait_uuid: UUID | None = None,
    ) -> "WProp":
        value_type_uuid = None if value_type is None else value_type.uuid
        existing = cls.by_key(owner, key)
        if existing is not None:
            live = existing._live_row()
            live.value_type_uuid = value_type_uuid
            live.value_trait_uuid = value_trait_uuid
            live.position = position
            live.formula = formula
            return existing
        row = TABLE_Props(
            uuid=uuid4(),
            key=key,
            owner_type_uuid=owner.uuid,
            value_type_uuid=value_type_uuid,
            value_trait_uuid=value_trait_uuid,
            position=position,
            formula=formula,
        )
        Database.session.add(row)
        Database.session.flush()
        return cls(row)

    @databasemethod(commit=False)
    def value_type(self) -> "WType":
        from nylium.objects.wtype import WType

        if self._value_type_uuid is None:
            raise RuntimeError(
                f"prop {self.key!r} is trait-bound and has no concrete value type"
            )
        value_type = WType.by_uuid(self._value_type_uuid)
        if value_type is None:
            raise RuntimeError(f"prop {self.key!r} has dangling value type")
        return value_type

    @classmethod
    @databasemethod(commit=False)
    def _attached_trait_uuids(cls, owner: "WType") -> list[UUID]:
        """Traits attached to `owner`, in attach order (ADR-0013)."""
        return list(
            Database.session.scalars(
                sqla.select(TABLE_TypeTraits.trait_uuid)
                .where(TABLE_TypeTraits.type_uuid == owner.uuid)
                .order_by(TABLE_TypeTraits.position)
            ).all()
        )

    @classmethod
    @databasemethod(commit=False)
    def effective_for(cls, owner: "WType") -> "list[WProp]":
        """The *effective* schema: own props, then each attached trait's
        props in attach order (ADR-0013). Reads and renders use this;
        writes (sync_schema) stay own-only."""
        result = cls.all_for(owner)
        for trait_uuid in cls._attached_trait_uuids(owner):
            rows = Database.session.scalars(
                sqla.select(TABLE_Props)
                .where(TABLE_Props.owner_trait_uuid == trait_uuid)
                .order_by(TABLE_Props.position)
            ).all()
            result.extend(cls(row) for row in rows)
        return result

    @classmethod
    @databasemethod(commit=False)
    def effective_by_key(cls, owner: "WType", key: str) -> "WProp | None":
        """One prop of the effective schema by key: own props first, then
        attached traits in attach order (key collisions are rejected at
        attach time, so the first hit is the only hit)."""
        own = cls.by_key(owner, key)
        if own is not None:
            return own
        for trait_uuid in cls._attached_trait_uuids(owner):
            row = Database.session.scalar(
                sqla.select(TABLE_Props).where(
                    TABLE_Props.owner_trait_uuid == trait_uuid,
                    TABLE_Props.key == key,
                )
            )
            if row is not None:
                return cls(row)
        return None
