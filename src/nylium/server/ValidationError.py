from __future__ import annotations
from nylium.server.ApiError import ApiError
from typing import ClassVar


class ValidationError(ApiError):
    STATUS: ClassVar[int] = 422
    CODE: ClassVar[str] = "validation"
