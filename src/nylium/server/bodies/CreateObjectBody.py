from __future__ import annotations
from nylium.api.Api import Api
from nylium.ny.nyobject import ObjectView
from nylium.server.PropCodec import PropCodec
from nylium.ny.nyobject import PropValue
from pydantic.dataclasses import dataclass
from dataclasses import field
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class CreateObjectBody:
    type_name: str
    props: dict[str, PropValue] = field(default_factory=dict)

    @classmethod
    def route(cls, body: "CreateObjectBody") -> ObjectView:
        decoded = PropCodec.decode(body.type_name, body.props)
        return Api.create_object(body.type_name, decoded)


resolve_route_hints(sys.modules[__name__])
