from __future__ import annotations
from nylium.api.Api import Api
from nylium.api.ApiShared import ApiShared
from nylium.server.bodies.SyncEnumOptionItem import SyncEnumOptionItem
from nylium.data.views.TypeView import TypeView
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class SyncEnumOptionsBody:
    """The full option draft — renames by uuid (propagating to stored
    values), creates without, deletes whatever the draft omits unless
    still in use."""

    options: list[SyncEnumOptionItem]

    @classmethod
    def route(cls, name: str, body: "SyncEnumOptionsBody") -> TypeView:
        return ApiShared.type_view(
            Api.sync_enum_options(
                name, [(item.uuid, item.value) for item in body.options]
            )
        )


resolve_route_hints(sys.modules[__name__])
