"""File/Document/Image (ADR-0008): first-class file entities — uuid-stable
pointers to blobs under FILES_DIR. Covers MIME policies, rename-safety,
delete, and `img:<uuid>` type icons. Api-level; HTTP in test_http.py.
"""
from __future__ import annotations

import pytest

from nylium.api import Api
from nylium.objects.navigation import type_icon
from nylium.objects.nyfile import NyFile
from nylium.server.errors import ValidationError
from uuid import uuid4
from nylium.objects.nyobject import ArrayValue, ObjectRef, RefValue

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
PDF = b"%PDF-1.4 fake\n"


@pytest.fixture(autouse=True)
def _file_builtins() -> None:
    """Test DB is wiped per session; boot-seeding doesn't run here."""
    NyFile.ensure_builtins()


def upload(type_name: str, filename: str, mime: str, data: bytes = PNG):
    return Api.create_file(type_name, filename, mime, data)


def test_builtin_file_types_are_seeded():
    for name in NyFile.TYPE_NAMES:
        assert Api.get_type(name) is not None


def test_file_types_are_their_own_kind():
    for name in NyFile.TYPE_NAMES:
        view = Api.get_type(name)
        assert view is not None
        assert view.kind == "file"


def test_file_types_are_immutable():
    for name in NyFile.TYPE_NAMES:
        with pytest.raises(ValidationError):
            Api.delete_type(name)
        with pytest.raises(ValidationError):
            Api.rename_type(name, new_name=f"{name}2")
        with pytest.raises(ValidationError):
            Api.reorder_props(name, ["name"])
        with pytest.raises(ValidationError):
            Api.sync_props(name, [])


def test_file_accepts_any_mime():
    view = upload("File", "notes.xyz", "application/x-weird")
    assert view.name == "notes.xyz"
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
        upload("File", "big.bin", "application/octet-stream", b"\x00" * (NyFile.MAX_UPLOAD_BYTES + 1))


def test_blob_roundtrip_and_rename_safety():
    view = upload("Image", "a.png", "image/png", PNG)
    assert NyFile.blob_path(view.uuid).read_bytes() == PNG
    # rename is a display-name update — the uuid pointer never changes
    renamed = Api.rename_file(view.uuid, "b.png")
    assert renamed.name == "b.png"
    assert NyFile.blob_path(view.uuid).read_bytes() == PNG


def test_delete_removes_blob_and_row():
    view = upload("Image", "a.png", "image/png", PNG)
    assert NyFile.blob_path(view.uuid).is_file()
    assert Api.delete_file(view.uuid)
    assert not NyFile.blob_path(view.uuid).exists()
    assert Api.get_file(view.uuid) is None


def test_img_icon_validates_against_live_image():
    view = upload("Image", "icon.png", "image/png", PNG)
    icon = f"{NyFile.ICON_IMAGE_PREFIX}{view.uuid}"
    created = Api.create_type("Book", {"name": "String"}, "Books", icon=icon)
    assert type_icon(created.uuid) == icon


def test_img_icon_rejects_dead_uuid():

    with pytest.raises(ValidationError):
        Api.create_type("Book", {"name": "String"}, "Books", icon=f"{NyFile.ICON_IMAGE_PREFIX}{uuid4()}")


def test_img_icon_rejects_non_image_file():
    view = upload("File", "f.bin", "application/octet-stream")
    with pytest.raises(ValidationError):
        Api.create_type("Book", {"name": "String"}, "Books", icon=f"{NyFile.ICON_IMAGE_PREFIX}{view.uuid}")


def test_deleting_icon_image_resets_type_icon():
    view = upload("Image", "icon.png", "image/png", PNG)
    icon = f"{NyFile.ICON_IMAGE_PREFIX}{view.uuid}"
    created = Api.create_type("Book", {"name": "String"}, "Books", icon=icon)
    assert type_icon(created.uuid) == icon
    assert Api.delete_file(view.uuid)
    reloaded = Api.get_type("Book")
    assert reloaded is not None
    assert type_icon(reloaded.uuid) == NyFile.DEFAULT_GLYPH


def test_sweep_orphans_removes_untracked_blobs():
    view = upload("Image", "a.png", "image/png", PNG)
    orphan = NyFile.blob_path(view.uuid).parent / "deadbeef"
    orphan.write_bytes(b"junk")
    NyFile.sweep_orphans()
    assert not orphan.exists()
    assert NyFile.blob_path(view.uuid).is_file()


def test_file_prop_on_object_roundtrip():
    """ADR-0008: a user type holds a File/Image prop; the value is a
    files.uuid reference — stable across rename, cleared on delete."""

    _ = Api.create_type("Artwork", {"name": "String", "cover": "Image"}, "Artworks")
    cover = upload("Image", "cover.png", "image/png", PNG)
    obj = Api.create_object(
        "Artwork",
        {"name": "Mona", "cover": ObjectRef(uuid=cover.uuid, type_name="Image")},
    )
    assert obj.props["cover"] == RefValue(
        ref=ObjectRef(uuid=cover.uuid, type_name="Image")
    )

    # rename the file — the prop keeps pointing at the same uuid
    _ = Api.rename_file(cover.uuid, "renamed.png")
    reloaded = Api.get_object(obj.uuid)
    assert reloaded is not None
    assert reloaded.props["cover"] == RefValue(
        ref=ObjectRef(uuid=cover.uuid, type_name="Image")
    )

    # delete the file — the prop reference cascades away
    assert Api.delete_file(cover.uuid)
    reloaded = Api.get_object(obj.uuid)
    assert reloaded is not None
    assert reloaded.props["cover"] == RefValue(ref=None)


def test_file_prop_writes_plain_uuid():
    """A raw UUID is also a valid file-prop input (codec sends ObjectRef,
    but the Api accepts either)."""
    _ = Api.create_type("Artwork", {"name": "String", "cover": "Image"}, "Artworks")
    cover = upload("Image", "cover.png", "image/png", PNG)
    obj = Api.create_object("Artwork", {"name": "Mona", "cover": cover.uuid})

    assert obj.props["cover"] == RefValue(
        ref=ObjectRef(uuid=cover.uuid, type_name="Image")
    )


def test_array_of_image_stores_file_uuids():
    """ADR-0008: Array<Image> members are files.uuid, not box instances —
    the array stores the file pointer directly."""

    _ = Api.create_type(
        "Gallery", {"name": "String", "shots": "Array<Image>"}, "Galleries"
    )
    a = upload("Image", "a.png", "image/png", PNG)
    b = upload("Image", "b.png", "image/png", PNG)
    gal = Api.create_object(
        "Gallery",
        {
            "name": "g",
            "shots": [
                ObjectRef(uuid=a.uuid, type_name="Image"),
                ObjectRef(uuid=b.uuid, type_name="Image"),
            ],
        },
    )
    shots = gal.props["shots"]
    assert isinstance(shots, ArrayValue)
    assert shots.items == [
        RefValue(ref=ObjectRef(uuid=a.uuid, type_name="Image")),
        RefValue(ref=ObjectRef(uuid=b.uuid, type_name="Image")),
    ]
    # deleting one file drops its array member, leaving the rest intact
    assert Api.delete_file(a.uuid)
    reloaded = Api.get_object(gal.uuid)
    assert reloaded is not None
    shots_after = reloaded.props["shots"]
    assert isinstance(shots_after, ArrayValue)
    assert shots_after.items == [
        RefValue(ref=ObjectRef(uuid=b.uuid, type_name="Image")),
    ]
