# Docstring-level exception to the one-class-per-file doctrine: these are
# the response DTOs of a single HTTP boundary — splitting them would
# scatter one wire contract over eight files.
"""Typed route responses (ADR-0017): every route returns one of these
pydantic dataclasses (or a transport-level Response — see the ADR).

These replace the deleted table-side .wire() dicts. Field order and
names match web/src/contracts.ts exactly; pydantic's JSON mode renders
UUID and Decimal as strings, as .wire() did by hand.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from nylium.table_rows import File
from nylium.rows.objects import EnumOption, Prop, Trait, Type, UnitPart
from nylium.objects.navigation import (
    effective_props,
    prop_owner_trait,
    prop_value_type_name,
    trait_attached_names,
    trait_color,
    trait_props,
    type_color,
    type_enum_options,
    type_icon,
    type_plural_name,
    type_trait_names,
    type_unit_parts,
)

_CONFIG = ConfigDict(strict=True)


@dataclass(config=_CONFIG)
class PropView:
    """One prop of a type's effective schema (contracts.ts PropView)."""

    uuid: UUID
    key: str
    value_type: str
    formula: str | None
    collect: str | None
    trait: str | None
    trait_color: str | None

    @classmethod
    def from_row(cls, prop: Prop) -> Self:
        owner_trait = prop_owner_trait(prop)
        return cls(
            uuid=prop.uuid,
            key=prop.key,
            value_type=prop_value_type_name(prop),
            formula=prop.formula,
            collect=prop.collect,
            trait=None if owner_trait is None else owner_trait[0],
            trait_color=None if owner_trait is None else owner_trait[1],
        )


@dataclass(config=_CONFIG)
class EnumOptionView:
    """One enum option (contracts.ts EnumOptionView)."""

    uuid: UUID
    value: str

    @classmethod
    def from_row(cls, option: EnumOption) -> Self:
        return cls(uuid=option.uuid, value=option.value)


@dataclass(config=_CONFIG)
class UnitPartView:
    """One unit part (contracts.ts UnitPartView). Decimals cross as
    strings in pydantic JSON mode, losslessly."""

    uuid: UUID
    name: str
    multiplier: Decimal
    offset: Decimal
    is_base: bool

    @classmethod
    def from_row(cls, part: UnitPart) -> Self:
        return cls(
            uuid=part.uuid,
            name=part.name,
            multiplier=part.multiplier,
            offset=part.offset,
            is_base=part.is_base,
        )


@dataclass(config=_CONFIG)
class TraitView:
    """One trait with its own props and reverse attach list
    (contracts.ts TraitView)."""

    name: str
    color: str
    props: list[PropView]
    attached: list[str]

    @classmethod
    def from_row(cls, trait: Trait) -> Self:
        return cls(
            name=trait.name,
            color=trait_color(trait.uuid),
            props=[PropView.from_row(prop) for prop in trait_props(trait.uuid)],
            attached=list(trait_attached_names(trait.uuid)),
        )


@dataclass(config=_CONFIG)
class TypeView:
    """One type with its effective schema (contracts.ts TypeView)."""

    name: str
    plural_name: str
    icon: str
    color: str
    kind: str
    embedded: bool
    level: int
    traits: list[str]
    enum_options: list[EnumOptionView]
    unit_parts: list[UnitPartView]
    props: list[PropView]

    @classmethod
    def from_row(cls, type_: Type, level: int | None = None) -> Self:
        # Level is derived from the whole type graph, so it's computed on
        # demand when the caller didn't already batch it (see from_rows).
        if level is None:
            from nylium.api.shared import ApiShared
            from nylium.table_rows.objects import types

            level = ApiShared.reference_levels(list(types.all())).get(type_.name, 1)
        return cls(
            name=type_.name,
            plural_name=type_plural_name(type_.uuid),
            icon=type_icon(type_.uuid),
            color=type_color(type_.uuid),
            kind=type_.kind,
            embedded=type_.embedded,
            level=level,
            traits=type_trait_names(type_.uuid),
            enum_options=[
                EnumOptionView.from_row(option)
                for option in type_enum_options(type_.uuid)
            ],
            unit_parts=[UnitPartView.from_row(part) for part in type_unit_parts(type_.uuid)],
            props=[PropView.from_row(prop) for prop in effective_props(type_.uuid)],
        )

    @classmethod
    def from_rows(cls, rows: list[Type]) -> list[Self]:
        """Build all type views with levels computed once over the graph."""
        from nylium.api.shared import ApiShared

        levels = ApiShared.reference_levels(rows)
        return [cls.from_row(type_, levels.get(type_.name, 1)) for type_ in rows]


@dataclass(config=_CONFIG)
class FileView:
    """One stored file's metadata (contracts.ts FileView)."""

    uuid: UUID
    type_name: str
    name: str
    mime: str
    size_bytes: int

    @classmethod
    def from_row(cls, file: File) -> Self:
        return cls(
            uuid=file.uuid,
            type_name=file.type_name,
            name=file.name,
            mime=file.mime,
            size_bytes=file.size_bytes,
        )


@dataclass(config=_CONFIG)
class StorageStats:
    """Disk usage of the blob-store volume plus nylium's own footprint."""

    total_bytes: int
    used_bytes: int
    free_bytes: int
    nylium_bytes: int
