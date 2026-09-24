from __future__ import annotations
from typing import Annotated
from nylium.api.Api import Api
from nylium.objects.FileView import FileView
from nylium.server.bodies.shared import PATH_PARAMS
from dataclasses import dataclass as plain_dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


@plain_dataclass
class ListFilesRequest:
    """No-input request of GET /files."""

    @classmethod
    def route(cls, _request: Annotated["ListFilesRequest", PATH_PARAMS]) -> list[FileView]:
        return [FileView.from_row(file) for file in Api.list_files()]


resolve_route_hints(sys.modules[__name__])
