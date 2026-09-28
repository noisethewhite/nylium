from __future__ import annotations
from nylium.api import Api
from nylium.data.views import ObjectView
from uuid import UUID
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import api_route, resolve_route_hints
from nylium.Constants import Constants
from nylium.uuid import ObjectRef
@dataclass(config=Constants.Pydantic.CONFIG)
class SetInstancePropFunctionBody:
    """ADR-0029: bind a Function<T,R> to a prop of a specific object (None
    unbinds)."""
    function_uuid: UUID | None = None
    @classmethod
    @api_route("/objects/{object_uuid}/props/{prop_key}/function", "PUT")
    def route(
        cls, object_uuid: UUID, prop_key: str, body: "SetInstancePropFunctionBody"
    ) -> ObjectView:
        return Api.set_instance_prop_function(ObjectRef.of(object_uuid), prop_key, None if body.function_uuid is None else ObjectRef.of(body.function_uuid))
resolve_route_hints(sys.modules[__name__])
