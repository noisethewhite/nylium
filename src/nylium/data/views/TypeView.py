"""The type-schema wire projection (ADR-0017): TypeView, one type with
its effective schema, matching contracts.ts TypeView field-for-field.

Lives in its own module rather than nytype.py on purpose: nyprop imports
nytype (for value_type), so nytype must not import nyprop back — and a
pydantic view with list[PropView] fields needs PropView at class
creation time. The graph level cannot be computed here either (it needs
NyScalar — the NyScalar -> NyType -> NyProp cycle), so callers inject it;
ApiShared.type_view / type_views are the injection point.
"""
from __future__ import annotations

from typing import Self

from nylium.Constants import Constants
from pydantic.dataclasses import dataclass

from nylium.data.rows import Type
from nylium.uuid import TypeUUID
from nylium.data.views.EnumOptionView import EnumOptionView
from nylium.data.views.PropView import PropView
from nylium.data.views.UnitPartView import UnitPartView



@dataclass(config=Constants.Pydantic.VIEW_CONFIG)
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
    def from_row(cls, type_: Type, level: int) -> Self:
        # Level is derived from the whole type graph, which this layer
        # cannot see (cycle) — callers inject it (ApiShared.type_view /
        # type_views compute it once per request over the graph).
        return cls(
            name=type_.name,
            plural_name=TypeUUID.of(type_.uuid).plural_name(),
            icon=TypeUUID.of(type_.uuid).icon(),
            color=TypeUUID.of(type_.uuid).color(),
            kind=type_.kind,
            embedded=type_.embedded,
            level=level,
            traits=TypeUUID.of(type_.uuid).trait_names(),
            enum_options=[
                EnumOptionView.from_row(option)
                for option in TypeUUID.of(type_.uuid).enum_options()
            ],
            unit_parts=[UnitPartView.from_row(part) for part in TypeUUID.of(type_.uuid).unit_parts()],
            props=[PropView.from_row(prop) for prop in TypeUUID.of(type_.uuid).effective_props()],
        )
