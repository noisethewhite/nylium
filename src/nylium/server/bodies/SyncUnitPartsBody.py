from __future__ import annotations
from nylium.api import Api
from nylium.api import ApiShared
from nylium.server.bodies.SyncUnitPartItem import SyncUnitPartItem
from nylium.data.views import TypeView
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import api_route, resolve_route_hints
from nylium.Constants import Constants
@dataclass(config=Constants.Pydantic.CONFIG)
class SyncUnitPartsBody:
    """The full part draft — renames by uuid (propagating to stored
    values), creates without, deletes whatever the draft omits unless
    still in use. Exactly one part must carry is_base."""
    parts: list[SyncUnitPartItem]
    @classmethod
    @api_route("/units/{name}/parts", "PUT")
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
