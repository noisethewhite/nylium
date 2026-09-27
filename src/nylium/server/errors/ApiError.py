from __future__ import annotations
from typing import ClassVar


class ApiError(Exception):
    """Base domain error; subclasses pin a status code and wire code."""

    STATUS: ClassVar[int] = 500
    CODE: ClassVar[str] = "internal"

    message: str

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
