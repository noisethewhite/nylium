"""Type, enum, unit and prop request bodies and their routes (ADR-0017)."""
from __future__ import annotations

import sys

from dataclasses import dataclass as plain_dataclass, field
from decimal import Decimal
from typing import Annotated
from uuid import UUID
from fastapi.responses import Response
from pydantic.dataclasses import dataclass
from nylium.api.api import Api
from nylium.objects.wscalar import WColor
from nylium.server.bodies.shared import BODY_CONFIG, PATH_PARAMS, resolve_route_hints
from nylium.server.errors import NotFoundError
from nylium.server.views import TypeView


@dataclass(config=BODY_CONFIG)
class CreateTypeBody:
    """props maps prop key -> value type name, like Api.create_type."""

    name: str
    # ADR-0019+: optional — backend falls back to a naive `f"{name}s"`,
    # the frontend pre-fills it with a smarter guess as the user types
    plural_name: str | None = None
    props: dict[str, str] = field(default_factory=dict)
    # ADR-0005: optional prop key -> formula string
    formulas: dict[str, str] | None = None
    # ADR-0025: optional prop key -> collect member key
    collects: dict[str, str] | None = None
    icon: str = "inventory_2"
    color: str = WColor.DEFAULT
    # ADR-0004: composition type — instances exist only as prop values
    embedded: bool = False

    @classmethod
    def route(cls, body: "CreateTypeBody") -> TypeView:
        return TypeView.from_row(
            Api.create_type(
                body.name,
                body.props,
                body.plural_name,
                body.icon,
                body.color,
                body.embedded,
                body.formulas,
                body.collects,
            )
        )


@dataclass(config=BODY_CONFIG)
class CreateEnumBody:
    """A string enum type: name plus its allowed option values."""

    name: str
    options: list[str] = field(default_factory=list)
    icon: str = "lists"
    color: str = WColor.DEFAULT

    @classmethod
    def route(cls, body: "CreateEnumBody") -> TypeView:
        return TypeView.from_row(
            Api.create_enum(body.name, body.options, body.icon, body.color)
        )


@dataclass(config=BODY_CONFIG)
class SyncEnumOptionItem:
    """One row of the enum editor's draft: uuid None = new option."""

    value: str
    uuid: UUID | None = None


@dataclass(config=BODY_CONFIG)
class SyncEnumOptionsBody:
    """The full option draft — renames by uuid (propagating to stored
    values), creates without, deletes whatever the draft omits unless
    still in use."""

    options: list[SyncEnumOptionItem]

    @classmethod
    def route(cls, name: str, body: "SyncEnumOptionsBody") -> TypeView:
        return TypeView.from_row(
            Api.sync_enum_options(
                name, [(item.uuid, item.value) for item in body.options]
            )
        )


@dataclass(config=BODY_CONFIG)
class UnitSecondaryInput:
    """One secondary part of a new unit: name and the affine conversion
    factor (base = (entered - offset) / multiplier)."""

    name: str
    multiplier: Decimal
    offset: Decimal = Decimal(0)


@dataclass(config=BODY_CONFIG)
class CreateUnitBody:
    """A unit type: name, its base part, and optional secondary parts."""

    name: str
    base: str
    secondaries: list[UnitSecondaryInput] = field(default_factory=list)
    icon: str = "straighten"
    color: str = WColor.DEFAULT

    @classmethod
    def route(cls, body: "CreateUnitBody") -> TypeView:
        return TypeView.from_row(
            Api.create_unit(
                body.name,
                body.base,
                [
                    (item.name, item.multiplier, item.offset)
                    for item in body.secondaries
                ],
                body.icon,
                body.color,
            )
        )


@dataclass(config=BODY_CONFIG)
class SyncUnitPartItem:
    """One row of the unit editor's draft: uuid None = new part."""

    name: str
    multiplier: Decimal
    offset: Decimal = Decimal(0)
    is_base: bool = False
    uuid: UUID | None = None


@dataclass(config=BODY_CONFIG)
class SyncUnitPartsBody:
    """The full part draft — renames by uuid (propagating to stored
    values), creates without, deletes whatever the draft omits unless
    still in use. Exactly one part must carry is_base."""

    parts: list[SyncUnitPartItem]

    @classmethod
    def route(cls, name: str, body: "SyncUnitPartsBody") -> TypeView:
        return TypeView.from_row(
            Api.sync_unit_parts(
                name,
                [
                    (item.uuid, item.name, item.multiplier, item.offset, item.is_base)
                    for item in body.parts
                ],
            )
        )


@dataclass(config=BODY_CONFIG)
class ReorderPropsBody:
    """New ordering for a type's props, as a full list of prop keys."""

    keys: list[str]

    @classmethod
    def route(cls, name: str, body: "ReorderPropsBody") -> TypeView:
        return TypeView.from_row(Api.reorder_props(name, body.keys))


@dataclass(config=BODY_CONFIG)
class SyncPropItem:
    """One row of the type editor's draft: uuid None = new prop."""

    key: str
    value_type: str
    uuid: UUID | None = None
    # ADR-0005: a formula over the owner's Array<T> props, or None
    formula: str | None = None
    # ADR-0025: a collect member key on the Array<T>'s element type, or None
    collect: str | None = None


@dataclass(config=BODY_CONFIG)
class SyncPropsBody:
    """The full prop draft — renames/retypes by uuid, creates without,
    deletes whatever the draft omits."""

    props: list[SyncPropItem]

    @classmethod
    def route(cls, name: str, body: "SyncPropsBody") -> TypeView:
        return TypeView.from_row(
            Api.sync_props(
                name,
                [(item.uuid, item.key, item.value_type, item.formula) for item in body.props],
                {item.key: item.collect for item in body.props if item.collect is not None},
            )
        )


@dataclass(config=BODY_CONFIG)
class UpdateTypeBody:
    """PATCH semantics: only the listed fields change."""

    name: str | None = None
    plural_name: str | None = None
    icon: str | None = None
    color: str | None = None

    @classmethod
    def route(cls, name: str, body: "UpdateTypeBody") -> TypeView:
        return TypeView.from_row(
            Api.rename_type(name, body.name, body.plural_name, body.icon, body.color)
        )


@plain_dataclass
class TypeNameRequest:
    """Path-bound input of the single-type GET/DELETE routes."""

    name: str

    @classmethod
    def route_get(cls, request: Annotated["TypeNameRequest", PATH_PARAMS]) -> TypeView:
        type_ = Api.get_type(request.name)
        if type_ is None:
            raise NotFoundError(f"no type {request.name!r}")
        return TypeView.from_row(type_)

    @classmethod
    def route_delete(cls, request: Annotated["TypeNameRequest", PATH_PARAMS]) -> Response:
        if not Api.delete_type(request.name):
            raise NotFoundError(f"no type {request.name!r}")
        return Response(status_code=204)


@plain_dataclass
class ListTypesRequest:
    """No-input request of GET /types."""

    @classmethod
    def route(cls, _request: Annotated["ListTypesRequest", PATH_PARAMS]) -> list[TypeView]:
        return TypeView.from_rows(Api.list_types())


resolve_route_hints(sys.modules[__name__])
