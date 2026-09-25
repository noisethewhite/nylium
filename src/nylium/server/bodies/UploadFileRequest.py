from __future__ import annotations
from typing import Annotated
from nylium.api.Api import Api
from nylium.data.views.FileView import FileView
from nylium.server.bodies.shared import PATH_PARAMS
from fastapi import UploadFile
from dataclasses import dataclass as plain_dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


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


resolve_route_hints(sys.modules[__name__])
