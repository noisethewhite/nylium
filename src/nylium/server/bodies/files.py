"""File and storage request bodies and their routes (ADR-0008, ADR-0017)."""
from __future__ import annotations

import sys

from dataclasses import dataclass as plain_dataclass
from typing import Annotated
from uuid import UUID
from fastapi import UploadFile
from fastapi.responses import FileResponse, Response
from pydantic.dataclasses import dataclass
from nylium.api.api import Api
from nylium.server.bodies.shared import BODY_CONFIG, PATH_PARAMS, resolve_route_hints
from nylium.server.errors import NotFoundError
from nylium.objects.wfile import FileView, StorageStats, WFile


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


@plain_dataclass
class UploadFileRequest:
    """Query-bound input of the multipart upload route. The UploadFile
    itself is a transport-level parameter next to the dataclass."""

    type_name: str

    @classmethod
    def route(
        cls, request: Annotated["UploadFileRequest", PATH_PARAMS], file: UploadFile
    ) -> FileView:
        """Multipart upload; the declared MIME comes from the client and is
        validated against the target file type's policy in Api.create_file."""
        data = file.file.read()
        return FileView.from_row(
            Api.create_file(
                request.type_name,
                file.filename or "",
                file.content_type or "application/octet-stream",
                data,
            )
        )


@plain_dataclass
class ListFilesRequest:
    """No-input request of GET /files."""

    @classmethod
    def route(cls, _request: Annotated["ListFilesRequest", PATH_PARAMS]) -> list[FileView]:
        return [FileView.from_row(file) for file in Api.list_files()]


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
        path = WFile.blob_path(request.file_uuid)
        if not path.is_file():
            raise NotFoundError(f"blob for file {request.file_uuid} is missing")
        return FileResponse(path, media_type=file.mime, filename=file.name)


@plain_dataclass
class StorageRequest:
    """No-input request of GET /storage."""

    @classmethod
    def route(cls, _request: Annotated["StorageRequest", PATH_PARAMS]) -> StorageStats:
        stats = Api.storage_stats()
        return StorageStats(
            total_bytes=stats["total_bytes"],
            used_bytes=stats["used_bytes"],
            free_bytes=stats["free_bytes"],
            nylium_bytes=stats["nylium_bytes"],
        )


resolve_route_hints(sys.modules[__name__])
