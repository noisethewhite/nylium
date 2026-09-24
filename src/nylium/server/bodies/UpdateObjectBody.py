from __future__ import annotations
from nylium.api.Api import Api
from nylium.server.bodies.shared import BODY_CONFIG
from nylium.server.NotFoundError import NotFoundError
from nylium.objects.nyobject import ObjectView
from nylium.server.PropCodec import PropCodec
from nylium.objects.nyobject import PropValue
from uuid import UUID
from pydantic.dataclasses import dataclass
from dataclasses import field
import sys
from nylium.server.bodies.shared import resolve_route_hints


@dataclass(config=BODY_CONFIG)
class UpdateObjectBody:
    """PATCH semantics: only the listed props are touched."""

    props: dict[str, PropValue] = field(default_factory=dict)

    @classmethod
    def route(cls, object_uuid: UUID, body: "UpdateObjectBody") -> ObjectView:
        view = Api.get_object(object_uuid)
        if view is None:
            raise NotFoundError(f"no object {object_uuid}")
        decoded = PropCodec.decode(view.type_name, body.props)
        return Api.update_object(object_uuid, decoded)


resolve_route_hints(sys.modules[__name__])
