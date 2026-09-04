"""FastAPI application factory over the nylium Api facade."""
from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

from fastapi import Depends, FastAPI, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from nylium.auth.guard import require_user
from nylium.auth.routes import auth_routes
from nylium.api.views import ObjectView, TypeView
from nylium.database.database import Database
from nylium.database.tables import Base
from nylium.objects.wfile import WFile
from nylium.objects.wscalar import WScalar
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
        # re-stamp builtin scalar icons on every boot — they are canonical
        WScalar.ensure_builtins()
        # ADR-0006: File/Document/Image builtins + blob-dir orphan sweep
        WFile.ensure_builtins()
        WFile.sweep_orphans()
        app = FastAPI(title=cls.TITLE)
        cls._mount_api(app)
        errors.register(app)
        StaticSpa.mount(app, cls._dist_dir())
        return app

    @classmethod
    def _ensure_schema(cls) -> None:
        """create_all is idempotent — the server is self-sufficient on
        a fresh database. Existing deployments get in-place ALTERs below
        for columns added after their first boot."""
        Base.metadata.create_all(Database.engine)
        cls._migrate_schema()

    @classmethod
    def _migrate_schema(cls) -> None:
        """Idempotent column backfills; each clause is a no-op once applied."""
        statements = [
            "ALTER TABLE types ADD COLUMN IF NOT EXISTS icon TEXT NOT NULL DEFAULT 'inventory_2'",
            "ALTER TABLE types ADD COLUMN IF NOT EXISTS color TEXT NOT NULL DEFAULT '#9e9e9e'",
            "ALTER TABLE types ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'object'",
            "ALTER TABLE types ADD COLUMN IF NOT EXISTS embedded BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE numeric_values ADD COLUMN IF NOT EXISTS unit TEXT",
            "ALTER TABLE props ADD COLUMN IF NOT EXISTS formula TEXT",
            "ALTER TABLE instances ADD COLUMN IF NOT EXISTS owner_object_uuid UUID",
            "ALTER TABLE instances ADD COLUMN IF NOT EXISTS owner_prop_uuid UUID",
            # ADR-0005: color stores hex now — align the pre-existing default
            "ALTER TABLE types ALTER COLUMN color SET DEFAULT '#9e9e9e'",
        ]
        with Database.engine.begin() as connection:
            for statement in statements:
                _ = connection.execute(text(statement))
            cls._migrate_type_colors(connection)

    @classmethod
    def _migrate_type_colors(cls, connection: Connection) -> None:
        """ADR-0005: rewrite legacy named-palette type colors to their hex
        values. Idempotent — hex values never match a palette key."""
        from nylium.objects.wscalar import WColor

        for name, hex_value in WColor.LEGACY_PALETTE.items():
            _ = connection.execute(
                text("UPDATE types SET color = :hex WHERE color = :name"),
                {"hex": hex_value, "name": name},
            )

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
            f"{prefix}/enums", routes.create_enum, methods=["POST"],
            status_code=created, response_model=TypeView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/enums/{{name}}/options", routes.sync_enum_options,
            methods=["PUT"], response_model=TypeView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/units", routes.create_unit, methods=["POST"],
            status_code=created, response_model=TypeView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/units/{{name}}/parts", routes.sync_unit_parts,
            methods=["PUT"], response_model=TypeView, dependencies=guard,
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
            f"{prefix}/types/{{name}}/props", routes.sync_props,
            methods=["PUT"], response_model=TypeView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}", routes.update_type, methods=["PATCH"],
            response_model=TypeView, dependencies=guard,
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
        app.add_api_route(
            f"{prefix}/files", routes.upload_file, methods=["POST"],
            status_code=created, response_model=ObjectView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files/{{file_uuid}}", routes.download_file, methods=["GET"],
            dependencies=guard,
        )
