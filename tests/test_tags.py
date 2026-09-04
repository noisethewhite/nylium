"""Derived tags (ADR-0005): array membership projects back onto the
member object as a tag named "<owner name> → <prop key>". Nothing is
stored — the tag is recomputed on every read. Api-level; HTTP shape lives
in test_http.py."""

from nylium.api import Api, TagView
from nylium.objects.wscalar import WColor


def book_type():
    return Api.create_type("Book", {"name": "String", "title": "String"}, "Books")


def shelf_type():
    _ = book_type()
    return Api.create_type(
        "Shelf",
        {"name": "String", "label": "String", "books": "Array<Book>"},
        "Shelves",
    )


def test_object_in_one_array_has_one_tag():
    _ = shelf_type()
    book = Api.create_object("Book", {"name": "Dune"})
    shelf = Api.create_object("Shelf", {"name": "Sci-Fi", "books": [book.uuid]})

    reloaded = Api.get_object(book.uuid)
    assert reloaded is not None
    assert reloaded.tags == [
        TagView(
            owner_uuid=shelf.uuid,
            owner_name="Sci-Fi",
            prop_key="books",
            name="Sci-Fi → books",
            color=WColor.DEFAULT,
        )
    ]


def test_tag_carries_owner_type_color():
    _ = book_type()
    _ = Api.create_type(
        "Shelf",
        {"name": "String", "books": "Array<Book>"},
        "Shelves",
        color="#539bf5",
    )
    book = Api.create_object("Book", {"name": "Dune"})
    _ = Api.create_object("Shelf", {"name": "Sci-Fi", "books": [book.uuid]})

    reloaded = Api.get_object(book.uuid)
    assert reloaded is not None
    assert [tag.color for tag in reloaded.tags] == ["#539bf5"]

def test_object_in_three_owners_arrays_has_three_tags():
    _ = shelf_type()
    book = Api.create_object("Book", {"name": "Dune"})
    owners = [
        Api.create_object("Shelf", {"name": name, "books": [book.uuid]})
        for name in ("Alpha", "Beta", "Gamma")
    ]

    reloaded = Api.get_object(book.uuid)
    assert reloaded is not None
    assert reloaded.tags == [
        TagView(
            owner_uuid=owner.uuid,
            owner_name=name,
            prop_key="books",
            name=f"{name} → books",
            color=WColor.DEFAULT,
        )
        for owner, name in zip(owners, ("Alpha", "Beta", "Gamma"))
    ]


def test_object_in_two_props_has_two_tags():
    _ = book_type()
    _ = Api.create_type(
        "Shelf",
        {"name": "String", "books": "Array<Book>", "featured": "Array<Book>"},
        "Shelves",
    )
    book = Api.create_object("Book", {"name": "Dune"})
    shelf = Api.create_object(
        "Shelf",
        {"name": "Sci-Fi", "books": [book.uuid], "featured": [book.uuid]},
    )

    reloaded = Api.get_object(book.uuid)
    assert reloaded is not None
    assert reloaded.tags == [
        TagView(
            owner_uuid=shelf.uuid,
            owner_name="Sci-Fi",
            prop_key="books",
            name="Sci-Fi → books",
            color=WColor.DEFAULT,
        ),
        TagView(
            owner_uuid=shelf.uuid,
            owner_name="Sci-Fi",
            prop_key="featured",
            name="Sci-Fi → featured",
            color=WColor.DEFAULT,
        ),
    ]


def test_object_not_in_any_array_has_no_tags():
    _ = shelf_type()
    book = Api.create_object("Book", {"name": "Dune"})
    # a shelf with an empty array does not tag the (unrelated) book
    _ = Api.create_object("Shelf", {"name": "Empty", "books": []})

    reloaded = Api.get_object(book.uuid)
    assert reloaded is not None
    assert reloaded.tags == []


def test_renaming_owner_renames_tag():
    _ = shelf_type()
    book = Api.create_object("Book", {"name": "Dune"})
    shelf = Api.create_object("Shelf", {"name": "Sci-Fi", "books": [book.uuid]})

    _ = Api.update_object(shelf.uuid, {"name": "Fantasy"})
    reloaded = Api.get_object(book.uuid)
    assert reloaded is not None
    assert reloaded.tags == [
        TagView(
            owner_uuid=shelf.uuid,
            owner_name="Fantasy",
            prop_key="books",
            name="Fantasy → books",
            color=WColor.DEFAULT,
        )
    ]


def test_renaming_prop_key_renames_tag():
    view = shelf_type()
    book = Api.create_object("Book", {"name": "Dune"})
    shelf = Api.create_object("Shelf", {"name": "Sci-Fi", "books": [book.uuid]})

    items = [
        (
            prop.uuid,
            "items" if prop.key == "books" else prop.key,
            prop.value_type,
            prop.formula,
        )
        for prop in view.props
    ]
    _ = Api.sync_props("Shelf", items)

    reloaded = Api.get_object(book.uuid)
    assert reloaded is not None
    assert reloaded.tags == [
        TagView(
            owner_uuid=shelf.uuid,
            owner_name="Sci-Fi",
            prop_key="items",
            name="Sci-Fi → items",
            color=WColor.DEFAULT,
        )
    ]


def test_removing_from_array_removes_tag():
    _ = shelf_type()
    book = Api.create_object("Book", {"name": "Dune"})
    shelf = Api.create_object("Shelf", {"name": "Sci-Fi", "books": [book.uuid]})

    _ = Api.update_object(shelf.uuid, {"books": []})
    reloaded = Api.get_object(book.uuid)
    assert reloaded is not None
    assert reloaded.tags == []
