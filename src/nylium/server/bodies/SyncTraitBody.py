from __future__ import annotations
from nylium.api.Api import Api
from nylium.server.bodies.SyncTraitPropItem import SyncTraitPropItem
from nylium.objects.TraitView import TraitView
from uuid import UUID
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
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


resolve_route_hints(sys.modules[__name__])
