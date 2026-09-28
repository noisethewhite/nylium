from __future__ import annotations
from typing import Annotated
from nylium.api import Api
from nylium.server.bodies.shared import PATH_PARAMS, api_route
from nylium.data.views import TraitView
from dataclasses import dataclass as plain_dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
@plain_dataclass
class ListTraitsRequest:
    """No-input request of GET /traits."""
    @classmethod
    @api_route("/traits", "GET")
    def route(cls, _request: Annotated["ListTraitsRequest", PATH_PARAMS]) -> list[TraitView]:
        return [TraitView.from_row(trait) for trait in Api.list_traits()]
resolve_route_hints(sys.modules[__name__])
