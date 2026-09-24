from __future__ import annotations
from nylium.server.ApiError import ApiError
from typing import ClassVar


class ConflictError(ApiError):
    STATUS: ClassVar[int] = 409
    CODE: ClassVar[str] = "conflict"
