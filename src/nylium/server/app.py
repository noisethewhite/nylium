"""FastAPI application factory over the nylium Api facade."""
from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

from fastapi import Depends, FastAPI, status

from nylium.auth.guard import require_user
from nylium.auth.routes import auth_routes
from nylium.api.views import ObjectView, TypeView
from nylium.database.database import Database
from nylium.database.tables import Base
from nylium.server.errors import errors
from nylium.server.routes import routes
from nylium.server.static import StaticSpa


class NyliumApp:
    """Composition root for the HTTP surface."""

    TITLE: ClassVar[str] = "nylium"
    API_PREFIX: ClassVar[str] = "/api"
    DIST_ENV: ClassVar[str] = "NYLIUM_WEB_DIST"
    DEFAULT_DIST: ClassVar[Path] = Path("web") / "dist"

    @classmethod
    def create(cls) -> FastAPI:
        cls._ensure_schema()
        app = FastAPI(title=cls.TITLE)
        cls._mount_api(app)
        errors.register(app)
        StaticSpa.mount(app, cls._dist_dir())
        return app

    @classmethod
    def _ensure_schema(cls) -> None:
        """create_all is idempotent — the server is self-sufficient on
        a fresh database and a no-op on an existing one."""
        Base.metadata.create_all(Database.engine)

    @classmethod
    def _dist_dir(cls) -> Path:
        return Path(os.environ.get(cls.DIST_ENV, str(cls.DEFAULT_DIST)))

    @classmethod
    def _mount_api(cls, app: FastAPI) -> None:
        prefix = cls.API_PREFIX
        created = status.HTTP_201_CREATED
        no_content = status.HTTP_204_NO_CONTENT
        guard = [Depends(require_user)]
        app.add_api_route(
            f"{prefix}/auth/register/start", auth_routes.register_start,
            methods=["POST"],
        )
        app.add_api_route(
            f"{prefix}/auth/register/finish", auth_routes.register_finish,
            methods=["POST"],
        )
        app.add_api_route(
            f"{prefix}/auth/login/start", auth_routes.login_start,
            methods=["POST"],
        )
        app.add_api_route(
            f"{prefix}/auth/login/finish", auth_routes.login_finish,
            methods=["POST"],
        )
        app.add_api_route(
            f"{prefix}/auth/logout", auth_routes.logout, methods=["POST"],
        )
        app.add_api_route(
            f"{prefix}/auth/me", auth_routes.me, methods=["GET"],
            dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types", routes.list_types, methods=["GET"],
            response_model=list[TypeView], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types", routes.create_type, methods=["POST"],
            status_code=created, response_model=TypeView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}", routes.get_type, methods=["GET"],
            response_model=TypeView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}", routes.delete_type, methods=["DELETE"],
            status_code=no_content, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}/props-order", routes.reorder_props,
            methods=["PATCH"], response_model=TypeView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/objects", routes.list_objects, methods=["GET"],
            response_model=list[ObjectView], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/objects", routes.create_object, methods=["POST"],
            status_code=created, response_model=ObjectView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/objects/{{object_uuid}}", routes.get_object, methods=["GET"],
            response_model=ObjectView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/objects/{{object_uuid}}", routes.update_object, methods=["PATCH"],
            response_model=ObjectView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/objects/{{object_uuid}}", routes.delete_object, methods=["DELETE"],
            status_code=no_content, dependencies=guard,
        )
