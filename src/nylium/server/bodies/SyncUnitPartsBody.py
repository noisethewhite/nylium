from __future__ import annotations
from nylium.api.Api import Api
from nylium.api.ApiShared import ApiShared
from nylium.server.bodies.SyncUnitPartItem import SyncUnitPartItem
from nylium.data.views.TypeView import TypeView
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class SyncUnitPartsBody:
    """The full part draft — renames by uuid (propagating to stored
    values), creates without, deletes whatever the draft omits unless
    still in use. Exactly one part must carry is_base."""

    parts: list[SyncUnitPartItem]

    @classmethod
    def route(cls, name: str, body: "SyncUnitPartsBody") -> TypeView:
        return ApiShared.type_view(
            Api.sync_unit_parts(
                name,
                [
                    (item.uuid, item.name, item.multiplier, item.offset, item.is_base)
                    for item in body.parts
                ],
            )
        )


resolve_route_hints(sys.modules[__name__])
