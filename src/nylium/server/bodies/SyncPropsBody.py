from __future__ import annotations
from nylium.api.Api import Api
from nylium.api.ApiShared import ApiShared
from nylium.server.bodies.SyncPropItem import SyncPropItem
from nylium.objects.TypeView import TypeView
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class SyncPropsBody:
    """The full prop draft — renames/retypes by uuid, creates without,
    deletes whatever the draft omits."""

    props: list[SyncPropItem]

    @classmethod
    def route(cls, name: str, body: "SyncPropsBody") -> TypeView:
        return ApiShared.type_view(
            Api.sync_props(
                name,
                [(item.uuid, item.key, item.value_type, item.formula) for item in body.props],
                {item.key: item.collect for item in body.props if item.collect is not None},
            )
        )


resolve_route_hints(sys.modules[__name__])
