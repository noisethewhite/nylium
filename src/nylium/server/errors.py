"""Domain error hierarchy -> one uniform JSON error response.

Everything a request can raise is funneled through a single wire shape:

    {"error": {"code": "<code>", "message": "<message>"}}

``ApiError`` and its subclasses carry their own status/code. Legacy
builtins still raised in the api/codec layers (KeyError, ValueError,
TypeError, PermissionError) are mapped here; FastAPI's
RequestValidationError and any truly unexpected exception are mapped
too. Only fatal startup errors (missing env vars, unparsable config)
may crash the process — never a request.
"""
from __future__ import annotations

import logging
from typing import ClassVar, cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic_core import ErrorDetails
from starlette.exceptions import HTTPException as StarletteHTTPException

_logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Base domain error; subclasses pin a status code and wire code."""

    STATUS: ClassVar[int] = 500
    CODE: ClassVar[str] = "internal"

    message: str

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(ApiError):
    STATUS: ClassVar[int] = 404
    CODE: ClassVar[str] = "not_found"


class ConflictError(ApiError):
    STATUS: ClassVar[int] = 409
    CODE: ClassVar[str] = "conflict"


class ValidationError(ApiError):
    STATUS: ClassVar[int] = 422
    CODE: ClassVar[str] = "validation"


class UnauthorizedError(ApiError):
    STATUS: ClassVar[int] = 401
    CODE: ClassVar[str] = "unauthorized"


class errors:
    """Namespace-only owner for the exception handlers (snake_case by
    doctrine: it groups behavior, it is never instantiated)."""

    INTERNAL_CODE: ClassVar[str] = "internal"
    INTERNAL_MESSAGE: ClassVar[str] = "internal server error"

    @classmethod
    def register(cls, app: FastAPI) -> None:
        app.add_exception_handler(ApiError, cls.api_error)
        app.add_exception_handler(KeyError, cls.not_found)
        app.add_exception_handler(ValueError, cls.conflict)
        app.add_exception_handler(TypeError, cls.validation)
        app.add_exception_handler(PermissionError, cls.unauthorized)
        app.add_exception_handler(RequestValidationError, cls.request_validation)
        app.add_exception_handler(StarletteHTTPException, cls.http_exception)
        app.add_exception_handler(Exception, cls.internal)

    @classmethod
    def api_error(cls, _request: Request, exc: Exception) -> JSONResponse:
        api_exc = cast(ApiError, exc)
        return cls._json(api_exc.STATUS, api_exc.CODE, api_exc.message)

    @classmethod
    def not_found(cls, _request: Request, exc: Exception) -> JSONResponse:
        return cls._json(
            status.HTTP_404_NOT_FOUND, NotFoundError.CODE, cls._message(exc)
        )

    @classmethod
    def conflict(cls, _request: Request, exc: Exception) -> JSONResponse:
        return cls._json(
            status.HTTP_409_CONFLICT, ConflictError.CODE, cls._message(exc)
        )

    @classmethod
    def validation(cls, _request: Request, exc: Exception) -> JSONResponse:
        return cls._json(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ValidationError.CODE,
            cls._message(exc),
        )

    @classmethod
    def unauthorized(cls, _request: Request, exc: Exception) -> JSONResponse:
        return cls._json(
            status.HTTP_401_UNAUTHORIZED, UnauthorizedError.CODE, cls._message(exc)
        )

    @classmethod
    def request_validation(cls, _request: Request, exc: Exception) -> JSONResponse:
        validation_exc = cast(RequestValidationError, exc)
        return cls._json(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ValidationError.CODE,
            cls._validation_message(validation_exc),
        )

    @classmethod
    def http_exception(cls, _request: Request, exc: Exception) -> JSONResponse:
        http_exc = cast(StarletteHTTPException, exc)
        message = http_exc.detail if http_exc.detail else "request failed"
        return cls._json(
            http_exc.status_code, cls._code_for(http_exc.status_code), message
        )

    @classmethod
    def _code_for(cls, status_code: int) -> str:
        known = {
            status.HTTP_400_BAD_REQUEST: ValidationError.CODE,
            status.HTTP_401_UNAUTHORIZED: UnauthorizedError.CODE,
            status.HTTP_403_FORBIDDEN: UnauthorizedError.CODE,
            status.HTTP_404_NOT_FOUND: NotFoundError.CODE,
            status.HTTP_409_CONFLICT: ConflictError.CODE,
            status.HTTP_422_UNPROCESSABLE_CONTENT: ValidationError.CODE,
        }
        return known.get(status_code, "request_error")

    @classmethod
    def internal(cls, _request: Request, exc: Exception) -> JSONResponse:
        _logger.exception("unhandled exception in request", exc_info=exc)
        return cls._json(
            status.HTTP_500_INTERNAL_SERVER_ERROR, cls.INTERNAL_CODE, cls.INTERNAL_MESSAGE
        )

    @classmethod
    def _message(cls, exc: Exception) -> str:
        first: object = exc.args[0] if exc.args else ""
        return first if isinstance(first, str) else str(exc)

    @classmethod
    def _validation_message(cls, exc: RequestValidationError) -> str:
        details = [
            f"{cls._path(error['loc'])}: {error['msg']}"
            for error in cast(list[ErrorDetails], exc.errors())
        ]
        return "; ".join(details) if details else "invalid request"

    @classmethod
    def _path(cls, location: object) -> str:
        if not isinstance(location, (tuple, list)):
            return str(location)
        parts = [str(part) for part in cast(list[object], location)]
        return ".".join(parts) if parts else "request"

    @classmethod
    def _json(cls, status_code: int, code: str, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={"error": {"code": code, "message": message}},
        )
