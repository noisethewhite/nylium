from __future__ import annotations
from typing import ClassVar
from nylium.database import Database
from nylium.system.Environment import Environment
from nylium.ny.NyType import NyType
from pathlib import Path
from nylium.data.tables import TypeStyles
from nylium.uuid import FileUUID, ObjectUUID
from nylium.data.tables import files
import logging


class NyFile:
    """Namespace for the file-type machinery — not a NyObject subclass:
    file instances are plain object-kind rows plus a blob on disk."""

    TYPE_FILE: ClassVar[str] = "File"
    TYPE_DOCUMENT: ClassVar[str] = "Document"
    TYPE_IMAGE: ClassVar[str] = "Image"
    TYPE_NAMES: ClassVar[frozenset[str]] = frozenset(
        {TYPE_FILE, TYPE_DOCUMENT, TYPE_IMAGE}
    )
    ICONS: ClassVar[dict[str, str]] = {
        TYPE_FILE: "draft",
        TYPE_DOCUMENT: "description",
        TYPE_IMAGE: "image",
    }

    # ADR-0006: strict MIME for Document and Image, anything for File
    IMAGE_MIME_PREFIX: ClassVar[str] = "image/"
    DOCUMENT_MIMES: ClassVar[frozenset[str]] = frozenset(
        {
            "application/pdf",
            "application/msword",
            "application/rtf",
            "application/epub+zip",
            "text/plain",
            "text/markdown",
            "text/csv",
        }
    )
    DOCUMENT_MIME_PREFIXES: ClassVar[tuple[str, ...]] = (
        "application/vnd.openxmlformats-officedocument.",
        "application/vnd.oasis.opendocument.",
    )

    MAX_UPLOAD_BYTES: ClassVar[int] = 25 * 1024 * 1024
    ICON_IMAGE_PREFIX: ClassVar[str] = "img:"
    # fallback icon when a referenced Image is deleted (ADR-0006) —
    # matches the types.icon column default
    DEFAULT_GLYPH: ClassVar[str] = "inventory_2"

    @classmethod
    def storage_dir(cls) -> Path:

        path = Path(Environment.files_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def blob_path(cls, uuid: FileUUID) -> Path:
        return cls.storage_dir() / str(uuid)

    @classmethod
    def is_file_type(cls, type_name: str) -> bool:
        return type_name in cls.TYPE_NAMES

    @classmethod
    def accepts_mime(cls, type_name: str, mime: str) -> bool:
        if type_name == cls.TYPE_IMAGE:
            return mime.startswith(cls.IMAGE_MIME_PREFIX)
        if type_name == cls.TYPE_DOCUMENT:
            return mime in cls.DOCUMENT_MIMES or mime.startswith(
                cls.DOCUMENT_MIME_PREFIXES
            )
        return type_name == cls.TYPE_FILE

    @classmethod
    @Database.commit_after_this
    def ensure_builtins(cls) -> None:

        for name in cls.TYPE_NAMES:
            _ = NyType.ensure(name, icon=cls.ICONS[name], kind=NyType.KIND_FILE)

    @classmethod
    @Database.use_same_session
    def sweep_orphans(cls) -> None:
        """Crash-window cleanup: blobs on disk with no files row are
        deleted. Runs on boot; every survivor is logged."""

        live = {str(uuid) for uuid in files}
        for blob in cls.storage_dir().iterdir():
            if blob.is_file() and blob.name not in live:
                logging.getLogger("nylium").warning(
                    "deleting orphan blob %s", blob.name
                )
                blob.unlink()

    @classmethod
    def delete_blob(cls, uuid: FileUUID) -> None:
        """Best-effort disk cleanup for a deleted instance. The DB row
        cascades with the instance; the blob cannot."""
        path = cls.blob_path(uuid)
        if path.is_file():
            path.unlink()

    @classmethod
    @Database.use_same_session
    def reset_icons_referencing(cls, image_uuid: FileUUID) -> None:
        """Deleting an Image used as an icon is allowed (ADR-0006): every
        type pointing at it falls back to the default glyph."""

        marker = f"{cls.ICON_IMAGE_PREFIX}{image_uuid}"
        TypeStyles.reset_icons_referencing(marker, cls.DEFAULT_GLYPH)

    @classmethod
    def parse_icon_image(cls, icon: str) -> FileUUID | None:
        """types.icon either names a Material glyph or `img:<uuid>` of an
        Image instance. Returns the uuid for the latter, None otherwise."""
        if not icon.startswith(cls.ICON_IMAGE_PREFIX):
            return None
        try:
            return FileUUID(icon[len(cls.ICON_IMAGE_PREFIX) :])
        except ValueError:
            return None

    @classmethod
    @Database.use_same_session
    def image_file_exists(cls, uuid: FileUUID) -> bool:
        return files.type_name_of(uuid) == cls.TYPE_IMAGE

    @classmethod
    @Database.use_same_session
    def clear_array_refs(cls, uuid: FileUUID) -> None:
        """Deleting a file also drops Array<File/Document/Image> members that
        pointed at it (ADR-0008) — mirrors NyObject.delete's cleanup of array
        links, so no dangling files.uuid survives in an array."""

        ObjectUUID.of(uuid).delete_memberships()
