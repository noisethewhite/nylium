"""WProp: handle on a row of the `props` table.

Owns the prop-level semantics (snapshots, effective schema across
attached traits); every statement lives in
``nylium.tables.objects.props`` / ``traits`` / ``type_traits`` (ADR-0019).
WType deliberately does not import WProp, so the dependency direction is
wprop -> wtype and nothing cycles.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar
from uuid import UUID

from nylium.database import databasemethod
from nylium.tables import TABLE_Props
from nylium.tables.objects.props import (
    SchemaItem as SchemaItem,
    apply_positions,
    by_trait_key,
    by_type_key,
    ensure_row,
    purge_values_for_instances as _purge_values_for_instances,
    rows_of_trait,
    rows_of_type,
    sync_owned,
)
from nylium.tables.objects.traits import name_of as trait_name_of
from nylium.tables.objects.type_traits import attached_trait_uuids

if TYPE_CHECKING:
    from nylium.objects.wtype import WType


class WProp:
    ROW: ClassVar[type[TABLE_Props]] = TABLE_Props

    def __init__(self, row: TABLE_Props):
        # snapshot for reads (session-independent); writes re-fetch their
        # rows inside the tables layer (ADR-0019)
        self._uuid: UUID = row.uuid
        self._key: str = row.key
        self._value_type_uuid: UUID | None = row.value_type_uuid
        self._value_trait_uuid: UUID | None = row.value_trait_uuid
        self._formula: str | None = row.formula
        self._collect: str | None = row.collect
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
    def collect(self) -> str | None:
        return self._collect

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
        name = trait_name_of(self._value_trait_uuid)
        if name is None:
            raise RuntimeError(f"prop {self.key!r} has a dangling value trait")
        return name

    @databasemethod(commit=False)
    def value_spec_name(self) -> str:
        """The wire-facing value spec: concrete type name, or
        ``Any<TraitName>`` for a trait-bound prop (ADR-0013)."""
        if self.is_trait_bound:
            return f"Any<{self.value_trait_name()}>"
        return self.value_type().name

    @classmethod
    @databasemethod(commit=False)
    def by_key(cls, owner: "WType", key: str) -> "WProp | None":
        row = by_type_key(owner.uuid, key)
        return None if row is None else cls(row)

    @classmethod
    @databasemethod(commit=False)
    def all_for(cls, owner: "WType") -> "list[WProp]":
        return [cls(row) for row in rows_of_type(owner.uuid)]

    @classmethod
    @databasemethod(commit=True)
    def reorder(cls, owner: "WType", keys: list[str]) -> None:
        """Rewrite positions so props render in `keys` order. The list
        must be a permutation of the whole schema — partial orders would
        silently orphan the props left out."""
        known = {prop.key for prop in cls.all_for(owner)}
        if set(keys) != known:
            raise ValueError(
                f"prop order {keys!r} does not match {owner.name!r} schema"
            )
        apply_positions(owner.uuid, keys)

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
        sync_owned(TABLE_Props.owner_type_uuid, "owner_type_uuid", owner.uuid, items)

    @classmethod
    @databasemethod(commit=True)
    def sync_trait_schema(cls, trait_uuid: UUID, items: list[SchemaItem]) -> None:
        """Same full-draft semantics as sync_schema, but the owner is a
        trait (ADR-0013). Retype purges values exactly like type-owned
        props."""
        sync_owned(TABLE_Props.owner_trait_uuid, "owner_trait_uuid", trait_uuid, items)

    @classmethod
    def purge_values_for_instances(cls, prop_uuid: UUID, inst_uuids: list[UUID]) -> None:
        """ADR-0013 detach: wipe this prop's values, but only on the given
        instances (the trait's other types keep theirs)."""
        _purge_values_for_instances(prop_uuid, inst_uuids)

    @classmethod
    @databasemethod(commit=True)
    def ensure(
        cls, owner: "WType", key: str, value_type: "WType | None",
        position: int = 0, formula: str | None = None,
        value_trait_uuid: UUID | None = None,
        collect: str | None = None,
    ) -> "WProp":
        value_type_uuid = None if value_type is None else value_type.uuid
        return cls(
            ensure_row(
                owner.uuid, key, value_type_uuid, value_trait_uuid, position,
                formula, collect,
            )
        )

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
    def effective_for(cls, owner: "WType") -> "list[WProp]":
        """The *effective* schema: own props, then each attached trait's
        props in attach order (ADR-0013). Reads and renders use this;
        writes (sync_schema) stay own-only."""
        result = cls.all_for(owner)
        for trait_uuid in attached_trait_uuids(owner.uuid):
            result.extend(cls(row) for row in rows_of_trait(trait_uuid))
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
        for trait_uuid in attached_trait_uuids(owner.uuid):
            row = by_trait_key(trait_uuid, key)
            if row is not None:
                return cls(row)
        return None
