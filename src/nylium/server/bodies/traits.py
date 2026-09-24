"""Trait request bodies and their routes (ADR-0013, ADR-0017)."""
from __future__ import annotations

import sys

from dataclasses import dataclass as plain_dataclass, field
from typing import Annotated
from uuid import UUID
from fastapi.responses import Response
from pydantic.dataclasses import dataclass
from nylium.api.Api import Api
from nylium.api.ApiShared import ApiShared
from nylium.objects.nyscalar import NyColor
from nylium.objects.TraitView import TraitView
from nylium.objects.TypeView import TypeView
from nylium.server.bodies.shared import BODY_CONFIG, PATH_PARAMS, resolve_route_hints
from nylium.server.errors import NotFoundError


@dataclass(config=BODY_CONFIG)
class CreateTraitBody:
    """A trait (ADR-0013): name, color, and a prop bundle — the same
    key -> value spec shape as CreateTypeBody.props."""

    name: str
    props: dict[str, str] = field(default_factory=dict)
    color: str = NyColor.DEFAULT

    @classmethod
    def route(cls, body: "CreateTraitBody") -> TraitView:
        return TraitView.from_row(Api.create_trait(body.name, body.color, body.props))


@dataclass(config=BODY_CONFIG)
class SyncTraitPropItem:
    """One row of the trait editor's draft: uuid None = new prop.
    Traits v1 have no formulas — no formula field."""

    key: str
    value_type: str
    uuid: UUID | None = None


@dataclass(config=BODY_CONFIG)
class SyncTraitBody:
    """PUT semantics: identity + the full prop draft (renames/retypes by
    uuid, creates without, deletes whatever the draft omits)."""

    name: str | None = None
    color: str | None = None
    props: list[SyncTraitPropItem] | None = None

    @classmethod
    def route(cls, name: str, body: "SyncTraitBody") -> TraitView:
        items: list[tuple[UUID | None, str, str, str | None]] | None = (
            None
            if body.props is None
            else [(item.uuid, item.key, item.value_type, None) for item in body.props]
        )
        return TraitView.from_row(Api.sync_trait(name, body.name, body.color, items))


@plain_dataclass
class TraitNameRequest:
    """Path-bound input of the single-trait GET/DELETE routes."""

    name: str

    @classmethod
    def route_get(cls, request: Annotated["TraitNameRequest", PATH_PARAMS]) -> TraitView:
        trait = Api.get_trait(request.name)
        if trait is None:
            raise NotFoundError(f"no trait {request.name!r}")
        return TraitView.from_row(trait)

    @classmethod
    def route_delete(cls, request: Annotated["TraitNameRequest", PATH_PARAMS]) -> Response:
        if not Api.delete_trait(request.name):
            raise NotFoundError(f"no trait {request.name!r}")
        return Response(status_code=204)


@plain_dataclass
class ListTraitsRequest:
    """No-input request of GET /traits."""

    @classmethod
    def route(cls, _request: Annotated["ListTraitsRequest", PATH_PARAMS]) -> list[TraitView]:
        return [TraitView.from_row(trait) for trait in Api.list_traits()]


@dataclass(config=BODY_CONFIG)
class TraitAttachBody:
    """Attach/detach a trait to/from a type."""

    trait: str

    @classmethod
    def route(cls, name: str, body: "TraitAttachBody") -> TypeView:
        return ApiShared.type_view(Api.attach_trait(name, body.trait))


@plain_dataclass
class DetachTraitRequest:
    """Path-bound input of DELETE /types/{name}/traits/{trait}."""

    name: str
    trait: str

    @classmethod
    def route(cls, request: Annotated["DetachTraitRequest", PATH_PARAMS]) -> TypeView:
        return ApiShared.type_view(Api.detach_trait(request.name, request.trait))


resolve_route_hints(sys.modules[__name__])
