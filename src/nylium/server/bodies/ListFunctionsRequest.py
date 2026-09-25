from __future__ import annotations
from typing import Annotated
from nylium.api.Api import Api
from nylium.data.views.FunctionView import FunctionView
from nylium.server.bodies.shared import PATH_PARAMS
from dataclasses import dataclass as plain_dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


@plain_dataclass
class ListFunctionsRequest:
    """No-input request of GET /functions."""

    @classmethod
    def route(cls, _request: Annotated["ListFunctionsRequest", PATH_PARAMS]) -> list[FunctionView]:
        return Api.list_functions()


resolve_route_hints(sys.modules[__name__])
