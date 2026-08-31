"""FastAPI application factory over the whiteout Api facade."""
from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

from fastapi import FastAPI, status

from whiteout.api.views import ObjectView, TypeView
from whiteout.server.errors import errors
from whiteout.server.routes import routes
from whiteout.server.static import StaticSpa


class WhiteoutApp:
    """Composition root for the HTTP surface."""

    TITLE: ClassVar[str] = "whiteout"
    API_PREFIX: ClassVar[str] = "/api"
    DIST_ENV: ClassVar[str] = "WHITEOUT_WEB_DIST"
    DEFAULT_DIST: ClassVar[Path] = Path("web") / "dist"

    @classmethod
    def create(cls) -> FastAPI:
        app = FastAPI(title=cls.TITLE)
        cls._mount_api(app)
        errors.register(app)
        StaticSpa.mount(app, cls._dist_dir())
        return app

    @classmethod
    def _dist_dir(cls) -> Path:
        return Path(os.environ.get(cls.DIST_ENV, str(cls.DEFAULT_DIST)))

    @classmethod
    def _mount_api(cls, app: FastAPI) -> None:
        prefix = cls.API_PREFIX
        created = status.HTTP_201_CREATED
        no_content = status.HTTP_204_NO_CONTENT
        app.add_api_route(
            f"{prefix}/types", routes.list_types, methods=["GET"],
            response_model=list[TypeView],
        )
        app.add_api_route(
            f"{prefix}/types", routes.create_type, methods=["POST"],
            status_code=created, response_model=TypeView,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}", routes.get_type, methods=["GET"],
            response_model=TypeView,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}", routes.delete_type, methods=["DELETE"],
            status_code=no_content,
        )
        app.add_api_route(
            f"{prefix}/objects", routes.list_objects, methods=["GET"],
            response_model=list[ObjectView],
        )
        app.add_api_route(
            f"{prefix}/objects", routes.create_object, methods=["POST"],
            status_code=created, response_model=ObjectView,
        )
        app.add_api_route(
            f"{prefix}/objects/{{object_uuid}}", routes.get_object, methods=["GET"],
            response_model=ObjectView,
        )
        app.add_api_route(
            f"{prefix}/objects/{{object_uuid}}", routes.update_object, methods=["PATCH"],
            response_model=ObjectView,
        )
        app.add_api_route(
            f"{prefix}/objects/{{object_uuid}}", routes.delete_object, methods=["DELETE"],
            status_code=no_content,
        )
