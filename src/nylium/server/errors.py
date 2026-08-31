"""Domain-error -> HTTP status mapping, registered on the app."""
from __future__ import annotations

from typing import ClassVar

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class errors:
    """Namespace-only owner for the exception handlers (snake_case by
    doctrine: it groups behavior, it is never instantiated)."""

    DETAIL_KEY: ClassVar[str] = "detail"

    @classmethod
    def register(cls, app: FastAPI) -> None:
        app.add_exception_handler(KeyError, cls.not_found)
        app.add_exception_handler(ValueError, cls.conflict)
        app.add_exception_handler(TypeError, cls.unprocessable)

    @classmethod
    def not_found(cls, _request: Request, exc: Exception) -> JSONResponse:
        return cls._json(status.HTTP_404_NOT_FOUND, exc)

    @classmethod
    def conflict(cls, _request: Request, exc: Exception) -> JSONResponse:
        return cls._json(status.HTTP_409_CONFLICT, exc)

    @classmethod
    def unprocessable(cls, _request: Request, exc: Exception) -> JSONResponse:
        return cls._json(status.HTTP_422_UNPROCESSABLE_CONTENT, exc)

    @classmethod
    def _json(cls, status_code: int, exc: Exception) -> JSONResponse:
        first: object = exc.args[0] if exc.args else ""
        message = first if isinstance(first, str) else str(exc)
        return JSONResponse(
            status_code=status_code, content={cls.DETAIL_KEY: message}
        )
