from __future__ import annotations
from nylium.server.ApiError import ApiError
from typing import ClassVar


class NotFoundError(ApiError):
    STATUS: ClassVar[int] = 404
    CODE: ClassVar[str] = "not_found"
