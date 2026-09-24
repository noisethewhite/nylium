from __future__ import annotations
from nylium.api.Api import Api
from nylium.server.bodies.shared import BODY_CONFIG
from nylium.objects.FileView import FileView
from nylium.server.NotFoundError import NotFoundError
from uuid import UUID
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


@dataclass(config=BODY_CONFIG)
class RenameFileBody:
    """ADR-0008: rename a file entity's display name. The uuid pointer is
    stable, so references never break."""

    name: str

    @classmethod
    def route(cls, file_uuid: UUID, body: "RenameFileBody") -> FileView:
        if Api.get_file(file_uuid) is None:
            raise NotFoundError(f"no file {file_uuid}")
        return FileView.from_row(Api.rename_file(file_uuid, body.name))


resolve_route_hints(sys.modules[__name__])
