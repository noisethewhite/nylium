"""File CRUD, blob lifecycle and storage stats (ADR-0015)."""
from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

from nylium.api.shared import ApiShared
from nylium.database import databasemethod
from nylium.tables import files
from nylium.tables.files import File
from nylium.objects.wfile import WFile


class FilesApi(ApiShared):
    @classmethod
    @databasemethod(commit=True)
    def create_file(
        cls, type_name: str, filename: str, mime: str, data: bytes
    ) -> File:
        """Atomic upload (ADR-0008): one transaction writes the `files` row,
        then the blob lands on disk last. If the disk write fails the
        transaction rolls back — no half-created pointer."""
        from nylium.server.errors import ValidationError

        if not WFile.is_file_type(type_name):
            raise ValidationError(
                f"type {type_name!r} is not a file type — use /api/files only for File/Document/Image"
            )
        if not filename.strip():
            raise ValidationError("filename must not be empty")
        if len(data) > WFile.MAX_UPLOAD_BYTES:
            raise ValidationError(
                f"file exceeds the {WFile.MAX_UPLOAD_BYTES // (1024 * 1024)} MiB upload cap"
            )
        if not WFile.accepts_mime(type_name, mime):
            raise ValidationError(
                f"{type_name} does not accept MIME {mime!r}"
            )
        file_uuid = uuid4()
        created = files.create(file_uuid, type_name, filename, mime, len(data))
        blob = WFile.blob_path(file_uuid)
        tmp = blob.with_suffix(".tmp")
        try:
            _ = tmp.write_bytes(data)
            _ = tmp.replace(blob)  # rename is atomic on the same filesystem
        finally:
            tmp.unlink(missing_ok=True)
        return created

    @classmethod
    @databasemethod(commit=False)
    def get_file(cls, uuid: UUID) -> File | None:
        return files.get(uuid)

    @classmethod
    @databasemethod(commit=False)
    def list_files(cls) -> list[File]:
        return list(files.values())

    @classmethod
    @databasemethod(commit=True)
    def rename_file(cls, uuid: UUID, name: str) -> File:
        """ADR-0008: rename is a display-name update — the uuid pointer is
        stable, so no reference ever breaks."""
        from nylium.server.errors import ValidationError

        if not name.strip():
            raise ValidationError("filename must not be empty")
        view = cls.get_file(uuid)
        if view is None:
            raise KeyError(f"no file {uuid}")
        view.name = name
        return view

    @classmethod
    @databasemethod(commit=True)
    def delete_file(cls, uuid: UUID) -> bool:
        """ADR-0008: drop the files row and the blob. An Image used as an
        icon resets every referencing type to the default glyph."""
        row = files.get(uuid)
        if row is None:
            return False
        if row.type_name == WFile.TYPE_IMAGE:
            WFile.reset_icons_referencing(uuid)
        WFile.clear_array_refs(uuid)
        files.delete(uuid)
        WFile.delete_blob(uuid)
        return True

    @classmethod
    def storage_stats(cls) -> dict[str, int]:
        """Disk usage of the volume that holds the blob store, plus
        nylium's own footprint (database + blobs). Read-only, no session
        needed — the size query goes through the engine directly."""
        import shutil

        import sqlalchemy as sqla

        from nylium.database import Database
        from nylium.objects.wfile import WFile

        storage = WFile.storage_dir()
        usage = shutil.disk_usage(storage)
        with Database.engine.connect() as connection:
            db_bytes = cast(
                int,
                connection.execute(
                    sqla.select(
                        sqla.func.pg_database_size(sqla.func.current_database())
                    )
                ).scalar_one(),
            )
        blob_bytes = sum(
            path.stat().st_size for path in storage.iterdir() if path.is_file()
        )
        return {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "nylium_bytes": db_bytes + blob_bytes,
        }
