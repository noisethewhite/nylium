"""Receipt analytics model (corrected): ReceiptItem is an embedded type
with a `product` ref and no `name` prop (ADR-0027 — embedded types may
omit `name`). Product's `price` is not a stored scalar but the ADR-0020
backlink projection of the ReceiptItems that reference it."""

from decimal import Decimal

from nylium.api import Api
from nylium.objects.quantity import Quantity


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
    assert [prop.key for prop in item_view.props] == [
        "product",
        "price",
        "quantity",
        "line_total",
    ]


def test_product_backlink_projects_receipt_item():
    _receipt_schema()
    product = Api.create_object("Product", {"name": "Olive Oil"})
    Api.create_object(
        "Receipt",
        {
            "name": "R1",
            "lines": [
                {
                    "product": product.uuid,
                    "price": Quantity(Decimal(5), "€"),
                    "quantity": Decimal(2),
                }
            ],
        },
    )

    reloaded = Api.get_object(product.uuid)
    assert reloaded is not None
    items = [ref for ref in reloaded.backlinks if ref.type_name == "ReceiptItem"]
    assert len(items) == 1
    assert items[0].type_name == "ReceiptItem"
