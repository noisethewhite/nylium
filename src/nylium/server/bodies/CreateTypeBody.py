from __future__ import annotations
from nylium.api.Api import Api
from nylium.api.ApiShared import ApiShared
from nylium.server.bodies.shared import BODY_CONFIG
from nylium.objects.NyColor import NyColor
from nylium.objects.TypeView import TypeView
from pydantic.dataclasses import dataclass
from dataclasses import field
import sys
from nylium.server.bodies.shared import resolve_route_hints


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
    color: str = NyColor.DEFAULT
    # ADR-0004: composition type — instances exist only as prop values
    embedded: bool = False

    @classmethod
    def route(cls, body: "CreateTypeBody") -> TypeView:
        return ApiShared.type_view(
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


resolve_route_hints(sys.modules[__name__])
