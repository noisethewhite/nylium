from __future__ import annotations
from nylium.api import Api
from nylium.data.views import ObjectView
from nylium.server.PropCodec import PropCodec
from nylium.data.views import PropValue
from pydantic.dataclasses import dataclass
from dataclasses import field
import sys
from nylium.server.bodies.shared import CREATED, api_route, resolve_route_hints
from nylium.Constants import Constants
@dataclass(config=Constants.Pydantic.CONFIG)
class CreateObjectBody:
    type_name: str
    props: dict[str, PropValue] = field(default_factory=dict)
    @classmethod
    @api_route("/objects", "POST", status_code=CREATED)
    def route(cls, body: "CreateObjectBody") -> ObjectView:
        decoded = PropCodec.decode(body.type_name, body.props)
        return Api.create_object(body.type_name, decoded)
resolve_route_hints(sys.modules[__name__])
