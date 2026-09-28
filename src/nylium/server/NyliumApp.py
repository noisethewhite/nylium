"""FastAPI application factory over the nylium Api facade."""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.engine import Connection

import nylium.server.bodies as bodies
from nylium.auth.guard import require_user
from nylium.auth.routes import auth_routes
from nylium.auth.token_routes import token_routes
from nylium.database import Database
from nylium.database.registry import reg
from nylium.ny.NyFile import NyFile
from nylium.ny.NyScalar import NyScalar
from nylium.server.bodies.shared import collect_route_specs
from nylium.server.errors import errors
from nylium.server.migrations import migrations
from nylium.server.StaticSpa import StaticSpa
from nylium.system.Environment import Environment
from typing import ClassVar
from nylium.ny.NyColor import NyColor


class NyliumApp:
    """Composition root for the HTTP surface."""

    TITLE: ClassVar[str] = "nylium"
    API_PREFIX: ClassVar[str] = "/api"

    @classmethod
    def create(cls) -> FastAPI:
        cls._ensure_schema()
        # re-stamp builtin scalar icons on every boot — they are canonical
        NyScalar.ensure_builtins()
        # ADR-0006: File/Document/Image builtins + blob-dir orphan sweep
        NyFile.ensure_builtins()
        NyFile.sweep_orphans()
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
            for statement in migrations.group("sql/schema"):
                _ = connection.execute(text(statement))
            cls._migrate_type_colors(connection)
            cls._migrate_file_kinds(connection)
            cls._migrate_files_to_first_class(connection)
            cls._migrate_decor(connection)

    @classmethod
    def _migrate_decor(cls, connection: Connection) -> None:
        """ADR-0014: decor columns leave types/traits for the 1:1
        type_style/trait_style tables (create_all made them). Backfill
        from the old columns if still present, then drop them. Runs last
        so _migrate_type_colors and the ADR-0005 color default have
        already normalized types.color."""
        for statement in migrations.group("sql/decor"):
            _ = connection.execute(text(statement))

    @classmethod
    def _migrate_file_kinds(cls, connection: Connection) -> None:
        """ADR-0006 follow-up: File/Document/Image are a dedicated kind, not
        object. Idempotent — re-running re-sets the same value."""
        _ = connection.execute(text(migrations.statement("sql/file_kinds.sql")))

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
        for statement in migrations.group("sql/files_first_class"):
            _ = connection.execute(text(statement))

    @classmethod
    def _migrate_type_colors(cls, connection: Connection) -> None:
        """ADR-0005: rewrite legacy named-palette type colors to their hex
        values. Idempotent — hex values never match a palette key. Runs
        before _migrate_decor so the decor backfill copies hex values;
        a no-op once types.color has moved to type_style (ADR-0014)."""

        has_column = connection.execute(
            text(migrations.statement("sql/type_colors/001_has_column.sql"))
        ).first()
        if has_column is None:
            return
        update = text(migrations.statement("sql/type_colors/002_update_color.sql"))
        for name, hex_value in NyColor.LEGACY_PALETTE.items():
            _ = connection.execute(update, {"hex": hex_value, "name": name})

    @classmethod
    def _dist_dir(cls) -> Path:
        return Path(str(Environment.web_dist))

    @classmethod
    def _mount_api(cls, app: FastAPI) -> None:
        prefix = cls.API_PREFIX
        guard = [Depends(require_user)]
        for spec in collect_route_specs(bodies, auth_routes, token_routes):
            if spec.handler is None:
                continue
            app.add_api_route(
                f"{prefix}{spec.path}", spec.handler, methods=[spec.method],
                status_code=spec.status_code,
                dependencies=guard if spec.guarded else None,
            )
