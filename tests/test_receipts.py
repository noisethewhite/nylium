"""Receipt analytics model (corrected): ReceiptItem is an embedded type
with a `product` ref and no `name` prop (ADR-0027 — embedded types may
omit `name`). Product's `price` is not a stored scalar but the ADR-0020
backlink projection of every ReceiptItem that references it — which needs
a true many-to-one link (ADR-0028), not the old 1-target-1-owner keying."""

from decimal import Decimal

from nylium.api import Api
from nylium.ny.nyobject import (
    ArrayValueView,
    EmbeddedValueView,
    ObjectRefView,
    RefValueView,
    ScalarValueView,
)
from nylium.data.types.Quantity import Quantity
from nylium.server.PropCodec import PropCodec
from nylium.api.ApiShared import ApiShared
from nylium.uuid import TypeUUID


def _currency() -> None:
    Api.create_unit("Currency", "€")


def _receipt_schema():
    _currency()
    Api.create_type("Product", {"name": "String"}, "Products")
    item_view = Api.create_type(
        "ReceiptItem",
        {
            "product": "Product",
            "price": "Numeric<Currency>",
            "quantity": "Numeric",
            "line_total": "Numeric<Currency>",
        },
        "ReceiptItems",
        embedded=True,
        formulas={"line_total": "price * quantity"},
    )
    Api.create_type(
        "Receipt", {"name": "String", "lines": "Array<ReceiptItem>"}, "Receipts"
    )
    return item_view


def test_receipt_item_embedded_without_name():
    item_view = _receipt_schema()
    # no `name` prop — the embedded type is name-less (ADR-0027)
    assert [prop.key for prop in TypeUUID.of(item_view.uuid).effective_props()] == [
        "product",
        "price",
        "quantity",
        "line_total",
    ]


def test_reference_levels_include_embedded_types():
    """Server-side reference-chain depth: Product -> 1 (leaf), ReceiptItem
    -> 2 (links `product: Product`), Receipt -> 3 (links
    `lines: Array<ReceiptItem>`). Embedded types are full nodes — a bug in
    the old frontend computation dropped them, flattening everything to 1."""
    _receipt_schema()
    views = ApiShared.type_views(Api.list_types())
    by_name = {view.name: view.level for view in views}
    assert by_name["Product"] == 1
    assert by_name["ReceiptItem"] == 2
    assert by_name["Receipt"] == 3



def test_product_backlink_projects_every_receipt_item():
    _receipt_schema()
    product = Api.create_object("Product", {"name": "Olive Oil"})
    # the same product bought on two receipts — many-to-one (ADR-0028)
    for name, price, qty in (("R1", Decimal(5), Decimal(2)), ("R2", Decimal(3), Decimal(1))):
        Api.create_object(
            "Receipt",
            {
                "name": name,
                "lines": [
                    {
                        "product": product.uuid,
                        "price": Quantity(price, "€"),
                        "quantity": qty,
                    }
                ],
            },
        )

    reloaded = Api.get_object(product.uuid)
    assert reloaded is not None
    items = [ref for ref in reloaded.backlinks if ref.type_name == "ReceiptItem"]
    assert len(items) == 2  # both receipts' lines point back at the product


def test_empty_embedded_array_element_is_dropped():
    """An Array<Embedded> draft with an all-empty element must not become a
    null row: the codec turns an empty draft into None ("no child") and the
    array decode drops it, instead of handing None to the array writer."""
    _receipt_schema()
    product = Api.create_object("Product", {"name": "Olive Oil"})
    decoded = PropCodec.decode(
        "Receipt",
        {
            "lines": ArrayValueView(
                items=[
                    EmbeddedValueView(
                        uuid=None,
                        type_name="ReceiptItem",
                        props={
                            "product": RefValueView(
                                ref=ObjectRefView(uuid=product.uuid, type_name="Product")
                            ),
                            "price": ScalarValueView(value="5.0", unit="€"),
                            "quantity": ScalarValueView(value="2"),
                        },
                    ),
                    EmbeddedValueView(uuid=None, type_name="ReceiptItem", props={}),
                ]
            )
        },
    )
    lines = decoded["lines"]
    assert isinstance(lines, list)
    assert len(lines) == 1  # the empty draft is dropped, not stored as None
    assert None not in lines
