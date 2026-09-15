"""Backlinks (ADR-0020): every link pointing at an object projects back
onto it as an ObjectRef — direct link props and array membership,
owners deduplicated. Nothing is stored — recomputed on every read.
Api-level; HTTP shape lives in test_http.py."""

from nylium.api import Api, ObjectRef


def author_book_types():
    _ = Api.create_type("Author", {"name": "String"}, "Authors")
    return Api.create_type(
        "Book",
        {"name": "String", "author": "Author", "related": "Array<Book>"},
        "Books",
    )


def test_object_without_incoming_links_has_no_backlinks():
    _ = author_book_types()
    book = Api.create_object("Book", {"name": "Dune"})

    reloaded = Api.get_object(book.uuid)
    assert reloaded is not None
    assert reloaded.backlinks == []


def test_direct_link_projects_backlink():
    _ = author_book_types()
    author = Api.create_object("Author", {"name": "Herbert"})
    book = Api.create_object("Book", {"name": "Dune", "author": author.uuid})

    reloaded = Api.get_object(author.uuid)
    assert reloaded is not None
    assert reloaded.backlinks == [ObjectRef(uuid=book.uuid, type_name="Book")]


def test_array_membership_projects_backlink():
    _ = author_book_types()
    dune = Api.create_object("Book", {"name": "Dune"})
    messiah = Api.create_object("Book", {"name": "Messiah", "related": [dune.uuid]})

    reloaded = Api.get_object(dune.uuid)
    assert reloaded is not None
    assert reloaded.backlinks == [ObjectRef(uuid=messiah.uuid, type_name="Book")]


def test_owner_linking_directly_and_via_array_appears_once():
    _ = Api.create_type("Label", {"name": "String"}, "Labels")
    _ = Api.create_type(
        "Note",
        {"name": "String", "primary": "Label", "labels": "Array<Label>"},
        "Notes",
    )
    label = Api.create_object("Label", {"name": "urgent"})
    note = Api.create_object(
        "Note", {"name": "n", "primary": label.uuid, "labels": [label.uuid]}
    )

    reloaded = Api.get_object(label.uuid)
    assert reloaded is not None
    assert reloaded.backlinks == [ObjectRef(uuid=note.uuid, type_name="Note")]


def test_direct_and_array_referrers_project_two_backlinks():
    _ = Api.create_type("Label", {"name": "String"}, "Labels")
    _ = Api.create_type(
        "Note",
        {"name": "String", "primary": "Label", "labels": "Array<Label>"},
        "Notes",
    )
    label = Api.create_object("Label", {"name": "urgent"})
    # instance_values is keyed by the target uuid, so a second DIRECT
    # link to the same target would replace the first — many→one
    # references go through arrays
    direct = Api.create_object("Note", {"name": "direct", "primary": label.uuid})
    via_array = Api.create_object("Note", {"name": "array", "labels": [label.uuid]})

    reloaded = Api.get_object(label.uuid)
    assert reloaded is not None
    assert {ref.uuid for ref in reloaded.backlinks} == {direct.uuid, via_array.uuid}
    assert all(ref.type_name == "Note" for ref in reloaded.backlinks)
