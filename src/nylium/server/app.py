"""FastAPI application factory over the nylium Api facade."""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from nylium.auth.guard import require_user
from nylium.auth.routes import auth_routes
from nylium.auth.token_routes import token_routes
from nylium.database import Database
from nylium.database.registry import reg
from nylium.objects.wfile import WFile
from nylium.objects.wscalar import WScalar
import nylium.server.bodies as bodies
from nylium.server.errors import errors
from nylium.server.migrations import migrations
from nylium.server.static import StaticSpa
from nylium.system.environment import Environment
from typing import ClassVar


class NyliumApp:
    """Composition root for the HTTP surface."""

    TITLE: ClassVar[str] = "nylium"
    API_PREFIX: ClassVar[str] = "/api"

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
        reg.metadata.create_all(Database.engine)
        cls._migrate_schema()

    @classmethod
    def _migrate_schema(cls) -> None:
        """Idempotent column backfills; each clause is a no-op once applied.

        SQL lives in the migrations resource package (ADR-0016); filename
        order inside each group is the execution order.
        """
        with Database.engine.begin() as connection:
            for statement in migrations.group("schema"):
                _ = connection.execute(text(statement))
            cls._migrate_type_colors(connection)
            cls._migrate_file_kinds(connection)
            cls._migrate_files_to_first_class(connection)
            cls._migrate_decor(connection)

    @classmethod
    def _migrate_decor(cls, connection: Connection) -> None:
        """ADR-0014: decor columns leave types/traits for the 1:1
        type_decor/trait_decor tables (create_all made them). Backfill
        from the old columns if still present, then drop them. Runs last
        so _migrate_type_colors and the ADR-0005 color default have
        already normalized types.color."""
        for statement in migrations.group("decor"):
            _ = connection.execute(text(statement))

    @classmethod
    def _migrate_file_kinds(cls, connection: Connection) -> None:
        """ADR-0006 follow-up: File/Document/Image are a dedicated kind, not
        object. Idempotent — re-running re-sets the same value."""
        _ = connection.execute(text(migrations.statement("file_kinds.sql")))

    @classmethod
    def _migrate_files_to_first_class(cls, connection: Connection) -> None:
        """ADR-0008: promote files to a self-contained table. Idempotent —
        every step is a no-op once applied.

        Order matters: we copy type_name/name and prop references into the
        new columns/table, then sever the instance FKs, THEN drop the file
        instances. If the instance FK is still live when the instances go,
        files.uuid's ON DELETE CASCADE would wipe the rows we just migrated.
        The numeric file prefixes encode exactly that order (ADR-0016).
        """
        for statement in migrations.group("files_first_class"):
            _ = connection.execute(text(statement))

    @classmethod
    def _migrate_type_colors(cls, connection: Connection) -> None:
        """ADR-0005: rewrite legacy named-palette type colors to their hex
        values. Idempotent — hex values never match a palette key. Runs
        before _migrate_decor so the decor backfill copies hex values;
        a no-op once types.color has moved to type_decor (ADR-0014)."""
        from nylium.objects.wscalar import WColor

        has_column = connection.execute(
            text(migrations.statement("type_colors/001_has_column.sql"))
        ).first()
        if has_column is None:
            return
        update = text(migrations.statement("type_colors/002_update_color.sql"))
        for name, hex_value in WColor.LEGACY_PALETTE.items():
            _ = connection.execute(update, {"hex": hex_value, "name": name})

    @classmethod
    def _dist_dir(cls) -> Path:
        return Path(str(Environment.web_dist))

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
            f"{prefix}/auth/tokens", token_routes.create, methods=["POST"],
        )
        app.add_api_route(
            f"{prefix}/auth/tokens", token_routes.list, methods=["GET"],
        )
        app.add_api_route(
            f"{prefix}/auth/tokens/{{token_uuid}}", token_routes.revoke,
            methods=["DELETE"],
        )
        app.add_api_route(
            f"{prefix}/types", bodies.ListTypesRequest.route, methods=["GET"],
            dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types", bodies.CreateTypeBody.route, methods=["POST"],
            status_code=created, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/enums", bodies.CreateEnumBody.route, methods=["POST"],
            status_code=created, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/enums/{{name}}/options", bodies.SyncEnumOptionsBody.route,
            methods=["PUT"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/units", bodies.CreateUnitBody.route, methods=["POST"],
            status_code=created, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/units/{{name}}/parts", bodies.SyncUnitPartsBody.route,
            methods=["PUT"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}", bodies.TypeNameRequest.route_get, methods=["GET"],
            dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}", bodies.TypeNameRequest.route_delete, methods=["DELETE"],
            status_code=no_content, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}/props-order", bodies.ReorderPropsBody.route,
            methods=["PATCH"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}/props", bodies.SyncPropsBody.route,
            methods=["PUT"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}", bodies.UpdateTypeBody.route, methods=["PATCH"],
            dependencies=guard,
        )
        # --- traits (ADR-0013) ---
        app.add_api_route(
            f"{prefix}/traits", bodies.ListTraitsRequest.route, methods=["GET"],
            dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/traits", bodies.CreateTraitBody.route, methods=["POST"],
            status_code=created, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/traits/{{name}}", bodies.TraitNameRequest.route_get, methods=["GET"],
            dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/traits/{{name}}", bodies.SyncTraitBody.route, methods=["PUT"],
            dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/traits/{{name}}", bodies.TraitNameRequest.route_delete, methods=["DELETE"],
            status_code=no_content, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}/traits", bodies.TraitAttachBody.route,
            methods=["POST"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/types/{{name}}/traits/{{trait}}", bodies.DetachTraitRequest.route,
            methods=["DELETE"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/objects", bodies.ListObjectsRequest.route, methods=["GET"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/objects", bodies.CreateObjectBody.route, methods=["POST"],
            status_code=created, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/objects/{{object_uuid}}", bodies.ObjectUuidRequest.route_get, methods=["GET"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/objects/{{object_uuid}}", bodies.UpdateObjectBody.route, methods=["PATCH"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/objects/{{object_uuid}}", bodies.ObjectUuidRequest.route_delete, methods=["DELETE"],
            status_code=no_content, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/objects/{{object_uuid}}/export", bodies.ObjectUuidRequest.route_export,
            methods=["GET"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/storage", bodies.StorageRequest.route, methods=["GET"],
            dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files", bodies.UploadFileRequest.route, methods=["POST"],
            status_code=created, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files", bodies.ListFilesRequest.route, methods=["GET"],
            dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files/{{file_uuid}}", bodies.FileUuidRequest.route_get, methods=["GET"],
            dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files/{{file_uuid}}", bodies.RenameFileBody.route, methods=["PATCH"],
            dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files/{{file_uuid}}", bodies.FileUuidRequest.route_delete, methods=["DELETE"],
            status_code=no_content, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/files/{{file_uuid}}/download", bodies.FileUuidRequest.route_download, methods=["GET"],
            dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/functions", bodies.ListFunctionsRequest.route, methods=["GET"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/functions", bodies.CreateFunctionBody.route, methods=["POST"],
            status_code=created, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/functions/{{function_uuid}}", bodies.FunctionUuidRequest.route_get, methods=["GET"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/functions/{{function_uuid}}", bodies.UpdateFunctionBody.route, methods=["PUT"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/functions/{{function_uuid}}", bodies.FunctionUuidRequest.route_delete, methods=["DELETE"],
            status_code=no_content, dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/objects/{{object_uuid}}/props/{{prop_key}}/function",
            bodies.SetInstancePropFunctionBody.route,
            methods=["PUT"], dependencies=guard,
        )
        # --- formula AST (ADR-0026) ---
        app.add_api_route(
            f"{prefix}/formulas/parse", bodies.FormulaParseBody.route,
            methods=["POST"], dependencies=guard,
        )
        app.add_api_route(
            f"{prefix}/formulas/render", bodies.FormulaRenderBody.route,
            methods=["POST"], dependencies=guard,
        )
