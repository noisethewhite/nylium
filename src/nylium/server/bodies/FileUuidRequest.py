from __future__ import annotations
from typing import Annotated
from nylium.api.Api import Api
from fastapi.responses import FileResponse
from nylium.objects.FileView import FileView
from nylium.server.NotFoundError import NotFoundError
from nylium.objects.NyFile import NyFile
from nylium.server.bodies.shared import PATH_PARAMS
from fastapi.responses import Response
from uuid import UUID
from dataclasses import dataclass as plain_dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints
from nylium.uuid import FileUUID


@plain_dataclass
class FileUuidRequest:
    """Path-bound input of the single-file routes."""

    file_uuid: UUID

    @classmethod
    def route_get(cls, request: Annotated["FileUuidRequest", PATH_PARAMS]) -> FileView:
        file = Api.get_file(request.file_uuid)
        if file is None:
            raise NotFoundError(f"no file {request.file_uuid}")
        return FileView.from_row(file)

    @classmethod
    def route_delete(cls, request: Annotated["FileUuidRequest", PATH_PARAMS]) -> Response:
        if not Api.delete_file(request.file_uuid):
            raise NotFoundError(f"no file {request.file_uuid}")
        return Response(status_code=204)

    @classmethod
    def route_download(cls, request: Annotated["FileUuidRequest", PATH_PARAMS]) -> FileResponse:

        file = Api.get_file(request.file_uuid)
        if file is None:
            raise NotFoundError(f"no file {request.file_uuid}")
        path = NyFile.blob_path(FileUUID.of(request.file_uuid))
        if not path.is_file():
            raise NotFoundError(f"blob for file {request.file_uuid} is missing")
        return FileResponse(path, media_type=file.mime, filename=file.name)


resolve_route_hints(sys.modules[__name__])
