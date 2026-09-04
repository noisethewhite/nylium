"""File/Document/Image (ADR-0006): instances are uuid-stable pointers to
blobs under FILES_DIR. Covers MIME policies, rename-safety, delete
cascade, and `img:<uuid>` type icons. Api-level; HTTP in test_http.py.
"""
from __future__ import annotations

import pytest

from nylium.api import Api
from nylium.objects.wfile import WFile
from nylium.server.errors import ValidationError

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
PDF = b"%PDF-1.4 fake\n"


@pytest.fixture(autouse=True)
def _file_builtins() -> None:
    """Test DB is wiped per session; boot-seeding doesn't run here."""
    WFile.ensure_builtins()


def upload(type_name: str, filename: str, mime: str, data: bytes = PNG):
    return Api.create_file(type_name, filename, mime, data)


def test_builtin_file_types_are_seeded():
    for name in WFile.TYPE_NAMES:
        assert Api.get_type(name) is not None


def test_file_accepts_any_mime():
    view = upload("File", "notes.xyz", "application/x-weird")
    assert view.props["name"].value == "notes.xyz"  # type: ignore[union-attr]
    meta = Api.get_file(view.uuid)
    assert meta is not None and meta.mime == "application/x-weird"


def test_image_rejects_non_image_mime():
    with pytest.raises(ValidationError):
        upload("Image", "doc.pdf", "application/pdf", PDF)


def test_document_rejects_image_mime():
    with pytest.raises(ValidationError):
        upload("Document", "pic.png", "image/png", PNG)


def test_document_accepts_pdf():
    view = upload("Document", "spec.pdf", "application/pdf", PDF)
    assert Api.get_file(view.uuid) is not None


def test_upload_rejects_unknown_type():
    with pytest.raises(ValidationError):
        upload("String", "x", "text/plain", b"hi")


def test_upload_cap():
    with pytest.raises(ValidationError):
        upload("File", "big.bin", "application/octet-stream", b"\x00" * (WFile.MAX_UPLOAD_BYTES + 1))


def test_blob_roundtrip_and_rename_safety():
    view = upload("Image", "a.png", "image/png", PNG)
    assert WFile.blob_path(view.uuid).read_bytes() == PNG
    # renaming is just a prop edit — the pointer is the uuid
    renamed = Api.update_object(view.uuid, {"name": "b.png"})
    assert renamed.props["name"].value == "b.png"  # type: ignore[union-attr]
    assert WFile.blob_path(view.uuid).read_bytes() == PNG


def test_delete_removes_blob_and_row():
    view = upload("Image", "a.png", "image/png", PNG)
    assert WFile.blob_path(view.uuid).is_file()
    assert Api.delete_object(view.uuid)
    assert not WFile.blob_path(view.uuid).exists()
    assert Api.get_file(view.uuid) is None


def test_img_icon_validates_against_live_image():
    view = upload("Image", "icon.png", "image/png", PNG)
    icon = f"{WFile.ICON_IMAGE_PREFIX}{view.uuid}"
    created = Api.create_type("Book", {"name": "String"}, "Books", icon=icon)
    assert created.icon == icon


def test_img_icon_rejects_dead_uuid():
    from uuid import uuid4

    with pytest.raises(ValidationError):
        Api.create_type("Book", {"name": "String"}, "Books", icon=f"{WFile.ICON_IMAGE_PREFIX}{uuid4()}")


def test_img_icon_rejects_non_image_file():
    view = upload("File", "f.bin", "application/octet-stream")
    with pytest.raises(ValidationError):
        Api.create_type("Book", {"name": "String"}, "Books", icon=f"{WFile.ICON_IMAGE_PREFIX}{view.uuid}")


def test_deleting_icon_image_resets_type_icon():
    view = upload("Image", "icon.png", "image/png", PNG)
    icon = f"{WFile.ICON_IMAGE_PREFIX}{view.uuid}"
    created = Api.create_type("Book", {"name": "String"}, "Books", icon=icon)
    assert created.icon == icon
    assert Api.delete_object(view.uuid)
    reloaded = Api.get_type("Book")
    assert reloaded is not None
    assert reloaded.icon == WFile.DEFAULT_GLYPH


def test_sweep_orphans_removes_untracked_blobs():
    view = upload("Image", "a.png", "image/png", PNG)
    orphan = WFile.blob_path(view.uuid).parent / "deadbeef"
    orphan.write_bytes(b"junk")
    WFile.sweep_orphans()
    assert not orphan.exists()
    assert WFile.blob_path(view.uuid).is_file()
