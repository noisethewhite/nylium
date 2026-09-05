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
from nylium.api.views import FileView, FunctionView, ObjectView, TypeView
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
            # ADR-0007: computed-scalar reference (mutually exclusive with formula)
            "ALTER TABLE props ADD COLUMN IF NOT EXISTS function_uuid UUID",
            # ADR-0005: color stores hex now — align the pre-existing default
            "ALTER TABLE types ALTER COLUMN color SET DEFAULT '#9e9e9e'",
        ]
        with Database.engine.begin() as connection:
            for statement in statements:
                _ = connection.execute(text(statement))
            cls._migrate_type_colors(connection)
            cls._migrate_file_kinds(connection)
            cls._migrate_files_to_first_class(connection)

    @classmethod
    def _migrate_file_kinds(cls, connection: Connection) -> None:
        """ADR-0006 follow-up: File/Document/Image are a dedicated kind, not
        object. Idempotent — re-running re-sets the same value."""
        _ = connection.execute(
            text("UPDATE types SET kind='file' WHERE name IN ('File','Document','Image')"),
        )

    @classmethod
    def _migrate_files_to_first_class(cls, connection: Connection) -> None:
        """ADR-0008: promote files to a self-contained table. Idempotent —
        every step is a no-op once applied.

        Order matters: we copy type_name/name and prop references into the
        new columns/table, then sever the instance FKs, THEN drop the file
        instances. If the instance FK is still live when the instances go,
        files.uuid's ON DELETE CASCADE would wipe the rows we just migrated.
        """
        file_types = "('File','Document','Image')"
        # 1. new columns (files.uuid stays the stable pointer)
        _ = connection.execute(
            text("ALTER TABLE files ADD COLUMN IF NOT EXISTS type_name TEXT")
        )
        _ = connection.execute(
            text("ALTER TABLE files ADD COLUMN IF NOT EXISTS name TEXT")
        )
        # 2. backfill type_name/name from the (soon-to-die) instances
        _ = connection.execute(
            text(
                "UPDATE files f SET type_name = t.name, name = COALESCE("
                + "  (SELECT sv.value FROM string_values sv JOIN props p ON sv.prop_uuid = p.uuid "
                + "   WHERE sv.inst_uuid = f.uuid AND p.key = 'name'), i.name) "
                + "FROM instances i JOIN types t ON i.type_uuid = t.uuid "
                + f"WHERE f.uuid = i.uuid AND t.name IN {file_types}"
            )
        )
        # orphan files rows (no instance) get a sane fallback before NOT NULL
        _ = connection.execute(
            text("UPDATE files SET type_name = 'File' WHERE type_name IS NULL")
        )
        _ = connection.execute(text("UPDATE files SET name = '' WHERE name IS NULL"))
        # 3. copy direct file references into file_values (keyed by
        #    owner instance + prop, pointing at files.uuid)
        _ = connection.execute(
            text(
                "INSERT INTO file_values (file_uuid, inst_uuid, prop_uuid) "
                + "SELECT iv.uuid, iv.inst_uuid, iv.prop_uuid FROM instance_values iv "
                + "JOIN instances i ON iv.uuid = i.uuid "
                + "JOIN types t ON i.type_uuid = t.uuid "
                + f"WHERE t.name IN {file_types} "
                + "ON CONFLICT (inst_uuid, prop_uuid) DO NOTHING"
            )
        )
        # 4. drop the old instance_values rows for file refs (now in
        #    file_values; their uuid FK -> instances would block step 8)
        _ = connection.execute(
            text(
                "DELETE FROM instance_values iv USING instances i, types t "
                + "WHERE iv.uuid = i.uuid AND i.type_uuid = t.uuid "
                + f"AND t.name IN {file_types}"
            )
        )
        # 5. sever array_values.value_uuid FK so Array<File/Document/Image>
        #    members (already holding the right files.uuid) survive step 8
        _ = connection.execute(
            text("ALTER TABLE array_values DROP CONSTRAINT IF EXISTS array_values_value_uuid_fkey")
        )
        # 6. sever files.uuid FK -> instances so file rows outlive instances
        _ = connection.execute(
            text("ALTER TABLE files DROP CONSTRAINT IF EXISTS files_uuid_fkey")
        )
        # 7. drop the redundant name prop on file types (cascades string_values)
        _ = connection.execute(
            text(
                "DELETE FROM props p USING types t WHERE p.owner_type_uuid = t.uuid "
                + f"AND t.name IN {file_types} AND p.key = 'name'"
            )
        )
        # 8. drop the file instances themselves (name scalar cascades away)
        _ = connection.execute(
            text(
                "DELETE FROM instances i USING types t WHERE i.type_uuid = t.uuid "
                + f"AND t.name IN {file_types}"
            )
        )
        # 9. lock the new columns
        _ = connection.execute(
            text("ALTER TABLE files ALTER COLUMN type_name SET NOT NULL")
        )
        _ = connection.execute(text("ALTER TABLE files ALTER COLUMN name SET NOT NULL"))

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
            f"{prefix}/objects/{{object_uuid}}/export", routes.export_object,
            methods=["GET"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files", routes.upload_file, methods=["POST"],
            status_code=created, response_model=FileView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files", routes.list_files, methods=["GET"],
            response_model=list[FileView], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files/{{file_uuid}}", routes.get_file, methods=["GET"],
            response_model=FileView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files/{{file_uuid}}", routes.rename_file, methods=["PATCH"],
            response_model=FileView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files/{{file_uuid}}", routes.delete_file, methods=["DELETE"],
            status_code=no_content, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files/{{file_uuid}}/download", routes.download_file, methods=["GET"],
            dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/functions", routes.list_functions, methods=["GET"],
            response_model=list[FunctionView], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/functions", routes.create_function, methods=["POST"],
            status_code=created, response_model=FunctionView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/functions/{{function_uuid}}", routes.get_function, methods=["GET"],
            response_model=FunctionView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/functions/{{function_uuid}}", routes.update_function, methods=["PUT"],
            response_model=FunctionView, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/functions/{{function_uuid}}", routes.delete_function, methods=["DELETE"],
            status_code=no_content, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}/props/{{prop_key}}/function",
            routes.set_prop_function,
            methods=["PUT"], response_model=TypeView, dependencies=guard,
        )
