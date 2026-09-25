from __future__ import annotations
from nylium.api.Api import Api
from nylium.objects.nyobject import ObjectView
from uuid import UUID
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants
from nylium.uuid import ObjectUUID


@dataclass(config=Constants.Pydantic.CONFIG)
class SetInstancePropFunctionBody:
    """ADR-0029: bind a Function<T,R> to a prop of a specific object (None
    unbinds)."""

    function_uuid: UUID | None = None

    @classmethod
    def route(
        cls, object_uuid: UUID, prop_key: str, body: "SetInstancePropFunctionBody"
    ) -> ObjectView:
        return Api.set_instance_prop_function(ObjectUUID.of(object_uuid), prop_key, None if body.function_uuid is None else ObjectUUID.of(body.function_uuid))


resolve_route_hints(sys.modules[__name__])
