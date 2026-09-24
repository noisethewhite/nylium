from __future__ import annotations
from nylium.server.ApiError import ApiError
from typing import ClassVar


class UnauthorizedError(ApiError):
    STATUS: ClassVar[int] = 401
    CODE: ClassVar[str] = "unauthorized"
