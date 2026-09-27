"""FastAPI application factory over the nylium Api facade."""
from __future__ import annotations

import importlib
import typing
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from nylium.auth.guard import require_user
from nylium.database import Database
from nylium.database.registry import reg
from nylium.ny.NyFile import NyFile
from nylium.ny.NyScalar import NyScalar
from nylium.server.errors import errors
from nylium.server.migrations import migrations
from nylium.server.RouteSpec import RouteSpec
from nylium.server.StaticSpa import StaticSpa
from nylium.system.Environment import Environment
from typing import ClassVar
from nylium.ny.NyColor import NyColor

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping


class NyliumApp:
    """Composition root for the HTTP surface."""

    TITLE: ClassVar[str] = "nylium"
    API_PREFIX: ClassVar[str] = "/api"
    CREATED: ClassVar[int] = status.HTTP_201_CREATED
    NO_CONTENT: ClassVar[int] = status.HTTP_204_NO_CONTENT

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
            for statement in migrations.group("schema"):
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
        a no-op once types.color has moved to type_style (ADR-0014)."""

        has_column = connection.execute(
            text(migrations.statement("type_colors/001_has_column.sql"))
        ).first()
        if has_column is None:
            return
        update = text(migrations.statement("type_colors/002_update_color.sql"))
        for name, hex_value in NyColor.LEGACY_PALETTE.items():
            _ = connection.execute(update, {"hex": hex_value, "name": name})

    @classmethod
    def _dist_dir(cls) -> Path:
        return Path(str(Environment.web_dist))

    @classmethod
    def api_route(
        cls,
        path: str,
        method: str,
        *,
        status_code: int | None = None,
        guarded: bool = True,
    ) -> Callable[[Callable[..., object]], Callable[..., object]]:
        """Stamp a route classmethod with its mount metadata, so _mount_api
        mounts every route from the declarations instead of a central
        add_api_route list. Sits UNDER @classmethod (sees the raw function).

        ``guarded=False`` marks the session-only / unauthenticated routes
        (auth ceremonies, token management) that skip the bearer guard —
        they carry their own auth dependency in the signature."""

        def decorator(fn: Callable[..., object]) -> Callable[..., object]:
            setattr(fn, "__route_spec__", RouteSpec(path, method, status_code, guarded))
            return fn

        return decorator

    @classmethod
    def _route_specs(cls, *owners: object) -> list[RouteSpec]:
        """Gather every api_route-stamped classmethod, with the handler
        bound to its owning class. Owners: a package (scans its __all__)
        or a namespace class directly."""
        specs: list[RouteSpec] = []
        for owner in owners:
            if isinstance(owner, ModuleType):
                candidates: list[object] = [
                    typing.cast("object", getattr(owner, export))
                    for export in typing.cast("list[str]", owner.__all__)
                ]
            else:
                candidates = [owner]
            for candidate in candidates:
                if not isinstance(candidate, type):
                    continue
                attrs = typing.cast("Mapping[str, object]", vars(candidate))
                for attr_name, member in attrs.items():
                    fn = getattr(member, "__func__", member)
                    spec = getattr(fn, "__route_spec__", None)
                    if not isinstance(spec, RouteSpec):
                        continue
                    handler = typing.cast(
                        "Callable[..., object]", getattr(candidate, attr_name)
                    )
                    specs.append(replace(spec, handler=handler))
        return specs

    @classmethod
    def _mount_api(cls, app: FastAPI) -> None:
        # Dynamic loading (not import statements, on purpose): bodies and
        # the auth namespaces stamp their routes via NyliumApp.api_route at
        # class-creation time, so they import this module — a static import
        # back would close the cycle in every static analyzer.
        bodies = importlib.import_module("nylium.server.bodies")
        auth_ns = typing.cast(
            "object",
            getattr(importlib.import_module("nylium.auth.routes"), "auth_routes"),
        )
        token_ns = typing.cast(
            "object",
            getattr(
                importlib.import_module("nylium.auth.token_routes"), "token_routes"
            ),
        )

        prefix = cls.API_PREFIX
        guard = [Depends(require_user)]
        for spec in cls._route_specs(bodies, auth_ns, token_ns):
            if spec.handler is None:
                continue
            app.add_api_route(
                f"{prefix}{spec.path}", spec.handler, methods=[spec.method],
                status_code=spec.status_code,
                dependencies=guard if spec.guarded else None,
            )
