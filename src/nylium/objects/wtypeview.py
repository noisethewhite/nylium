"""The type-schema wire projection (ADR-0017): TypeView, one type with
its effective schema, matching contracts.ts TypeView field-for-field.

Lives in its own module rather than wtype.py on purpose: wprop imports
wtype (for value_type), so wtype must not import wprop back — and a
pydantic view with list[PropView] fields needs PropView at class
creation time. The graph level cannot be computed here either (it needs
WScalar — the WScalar -> WType -> WProp cycle), so callers inject it;
ApiShared.type_view / type_views are the injection point.
"""
from __future__ import annotations

from typing import Self

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from nylium.data.rows import Type
from nylium.objects.navigation import (
    effective_props,
    type_color,
    type_enum_options,
    type_icon,
    type_plural_name,
    type_trait_names,
    type_unit_parts,
)
from nylium.objects.wenum import EnumOptionView
from nylium.objects.wprop import PropView
from nylium.objects.wunit import UnitPartView

_CONFIG = ConfigDict(strict=True)


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
    def from_row(cls, type_: Type, level: int) -> Self:
        # Level is derived from the whole type graph, which this layer
        # cannot see (cycle) — callers inject it (ApiShared.type_view /
        # type_views compute it once per request over the graph).
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
