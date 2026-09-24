"""Serves the built React bundle (web/dist) with SPA fallback.

An absent dist is fine: the app then serves only /api, and the vite
dev server owns the frontend during development.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import ClassVar, cast

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

FallbackHandler = Callable[[Request], Awaitable[Response]]


class StaticSpa:
    INDEX_FILE: ClassVar[str] = "index.html"
    ASSETS_DIR: ClassVar[str] = "assets"
    API_PREFIX: ClassVar[str] = "api"
    FALLBACK_ROUTE: ClassVar[str] = "/{full_path:path}"

    @classmethod
    def mount(cls, app: FastAPI, dist: Path) -> None:
        index = dist / cls.INDEX_FILE
        if not index.is_file():
            return
        assets = dist / cls.ASSETS_DIR
        if assets.is_dir():
            app.mount(
                f"/{cls.ASSETS_DIR}",
                StaticFiles(directory=assets),
                name=cls.ASSETS_DIR,
            )
        # registered after the API routes, so /api/* always wins first;
        # whatever /api path still misses must 404 as JSON, not as HTML
        app.add_route(
            cls.FALLBACK_ROUTE, cls._fallback(dist, index), methods=["GET"]
        )

    @classmethod
    def _fallback(cls, dist: Path, index: Path) -> FallbackHandler:
        root = dist.resolve()

        async def serve(request: Request) -> Response:
            # starlette types path_params as dict[str, Any]; the cast
            # states "unknown wire data" before the isinstance narrows it
            raw = cast(object, request.path_params.get("full_path", ""))
            path = raw if isinstance(raw, str) else ""
            if path == cls.API_PREFIX or path.startswith(cls.API_PREFIX + "/"):
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": f"no API route /{path}"},
                )
            file = (root / path).resolve()
            if file.is_relative_to(root) and file.is_file():
                return FileResponse(file)
            return FileResponse(index)

        return serve
