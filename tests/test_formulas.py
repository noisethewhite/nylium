"""Formula props (ADR-0005): storage, grammar, schema validation,
read-time evaluation, the write guard and rename-rewrite.

Api-level; HTTP shape lives in test_http.py."""

from decimal import Decimal

import pytest
from uuid import UUID

from nylium.api import Api, ArrayValueView, EmbeddedValueView, ScalarValueView
from nylium.data.types.Quantity import Quantity
from nylium.server.ValidationError import ValidationError
from nylium.uuid import TypeUUID
from nylium.uuid import PropUUID


def item_type():
    return Api.create_type(
        "Item", {"name": "String", "price": "Numeric", "label": "String"}, "Items"
    )


def receipt_type(formulas=None):
    _ = item_type()
    return Api.create_type(
        "Receipt",
        {
            "name": "String",
            "lines": "Array<Item>",
            "total": "Numeric",
            "count": "Integer",
        },
        "Receipts",
        formulas=formulas,
    )


def test_valid_formulas_stored_and_visible():
    view = receipt_type(
        {"total": "SUM(lines.price) * 1.21", "count": "COUNT(lines)"}
    )
    by_key = {prop.key: prop for prop in TypeUUID.of(view.uuid).effective_props()}
    assert by_key["total"].formula == "SUM(lines.price) * 1.21"
    assert by_key["count"].formula == "COUNT(lines)"
    # plain stored props default to None
    assert by_key["name"].formula is None
    assert by_key["lines"].formula is None


def test_unknown_function_rejected():
    with pytest.raises(ValidationError):
        receipt_type({"total": "MEDIAN(lines.price)"})


def test_unknown_array_key_rejected():
    with pytest.raises(ValidationError):
        receipt_type({"total": "SUM(stuff.price)"})


def test_non_array_key_rejected():
    with pytest.raises(ValidationError):
        receipt_type({"total": "SUM(name.price)"})


def test_unknown_member_prop_rejected():
    with pytest.raises(ValidationError):
        receipt_type({"total": "SUM(lines.weight)"})


def test_non_numeric_member_prop_rejected():
    with pytest.raises(ValidationError):
        receipt_type({"total": "SUM(lines.label)"})


def test_syntax_error_rejected():
    with pytest.raises(ValidationError):
        receipt_type({"total": "SUM("})


def test_non_count_bare_path_rejected():
    # only COUNT may take a bare array key without a member path
    with pytest.raises(ValidationError):
        receipt_type({"total": "SUM(items)"})


def test_formula_prop_must_be_numeric():
    with pytest.raises(ValidationError):
        _ = item_type()
        Api.create_type(
            "Bad",
            {"name": "String", "items": "Array<Item>", "total": "String"},
            "Bads",
            formulas={"total": "SUM(lines.price)"},
        )


def test_integer_formula_must_be_bare_count():
    with pytest.raises(ValidationError):
        receipt_type({"count": "SUM(lines.price)"})
    with pytest.raises(ValidationError):
        receipt_type({"count": "COUNT(lines.price)"})
    # ...while a Numeric prop may hold a bare COUNT too
    view = receipt_type({"total": "COUNT(lines)"})
    by_key = {prop.key: prop for prop in TypeUUID.of(view.uuid).effective_props()}
    assert by_key["total"].formula == "COUNT(lines)"


def test_formula_keys_must_name_props():
    with pytest.raises(ValidationError):
        receipt_type({"ghost": "SUM(lines.price)"})


def _sync_items(
    view, formulas
) -> list[tuple[UUID | None, str, str, str | None]]:
    return [
        (prop.uuid, prop.key, PropUUID.of(prop.uuid).value_type_name(), formulas.get(prop.key))
        for prop in TypeUUID.of(view.uuid).effective_props()
    ]


def test_sync_props_sets_updates_and_clears_formula():
    view = receipt_type()
    by_key = {prop.key: prop for prop in TypeUUID.of(view.uuid).effective_props()}
    assert by_key["total"].formula is None

    synced = Api.sync_props(
        "Receipt", _sync_items(view, {"total": "SUM(lines.price)"})
    )
    by_key = {prop.key: prop for prop in TypeUUID.of(synced.uuid).effective_props()}
    assert by_key["total"].formula == "SUM(lines.price)"

    synced = Api.sync_props(
        "Receipt", _sync_items(synced, {"total": "MAX(lines.price) + 1"})
    )
    by_key = {prop.key: prop for prop in TypeUUID.of(synced.uuid).effective_props()}
    assert by_key["total"].formula == "MAX(lines.price) + 1"

    synced = Api.sync_props("Receipt", _sync_items(synced, {}))
    by_key = {prop.key: prop for prop in TypeUUID.of(synced.uuid).effective_props()}
    assert by_key["total"].formula is None


def test_sync_props_validates_formula():
    view = receipt_type()
    with pytest.raises(ValidationError):
        Api.sync_props("Receipt", _sync_items(view, {"total": "SUM(lines.nope)"}))


# --- read-time evaluation ---


def _receipt(formulas, specs):
    receipt_type(formulas)
    items = [_item(name, price) for name, price in specs]
    return Api.create_object(
        "Receipt", {"name": "R1", "lines": [item.uuid for item in items]}
    )

def _item(name, price=None):
    item_type()
    props = {"name": name}
    if price is not None:
        props["price"] = Decimal(price)
    return Api.create_object("Item", props)


def test_eval_sum_over_items():
    receipt = _receipt(
        {"total": "SUM(lines.price)"},
        [("a", "10.5"), ("b", "2")],
    )
    view = Api.get_object(receipt.uuid)
    assert view is not None
    assert view.props["total"] == ScalarValueView(value=Decimal("12.5"))


def test_eval_arithmetic_and_integer_count():
    receipt = _receipt(
        {"total": "SUM(lines.price) * 1.21", "count": "COUNT(lines)"},
        [("a", "100"), ("b", "0")],
    )
    view = Api.get_object(receipt.uuid)
    assert view is not None
    assert view.props["total"] == ScalarValueView(value=Decimal("121.00"))
    # a bare COUNT on an Integer prop yields a plain int
    assert view.props["count"] == ScalarValueView(value=2)


def test_eval_unset_member_counts_zero():
    # COUNT with a member path is only legal on a Numeric prop, so fold it
    # into the total: SUM(10) + COUNT(set cells) = 11
    receipt = _receipt(
        {"total": "SUM(lines.price) + COUNT(lines.price)"},
        [("a", "10"), ("b", None)],
    )
    view = Api.get_object(receipt.uuid)
    assert view is not None
    assert view.props["total"] == ScalarValueView(value=Decimal("11"))


def test_eval_avg_min_max():
    receipt = _receipt(
        {"total": "AVERAGE(lines.price) + MIN(lines.price) + MAX(lines.price)"},
        [("a", "10"), ("b", "20"), ("c", "30")],
    )
    view = Api.get_object(receipt.uuid)
    assert view is not None
    assert view.props["total"] == ScalarValueView(value=Decimal("60"))


def test_eval_empty_array_aggregates_zero():
    receipt = _receipt({"total": "SUM(lines.price)", "count": "COUNT(lines)"}, [])
    view = Api.get_object(receipt.uuid)
    assert view is not None
    assert view.props["total"] == ScalarValueView(value=Decimal("0"))
    assert view.props["count"] == ScalarValueView(value=0)


def test_eval_division_by_zero_renders_empty():
    receipt = _receipt({"total": "SUM(lines.price) / COUNT(lines.price)"}, [])
    view = Api.get_object(receipt.uuid)
    assert view is not None
    assert view.props["total"] == ScalarValueView(value=None)


def test_eval_deleted_member_drops_out():
    receipt_type({"total": "SUM(lines.price)", "count": "COUNT(lines)"})
    kept = _item("a", "10")
    doomed = _item("b", "5")
    receipt = Api.create_object(
        "Receipt", {"name": "R1", "lines": [kept.uuid, doomed.uuid]}
    )
    assert Api.delete_object(doomed.uuid)
    view = Api.get_object(receipt.uuid)
    assert view is not None
    assert view.props["total"] == ScalarValueView(value=Decimal("10"))
    assert view.props["count"] == ScalarValueView(value=1)


# --- the write guard ---


def test_write_guard_create_and_update():
    receipt_type({"total": "SUM(lines.price)"})
    with pytest.raises(ValidationError):
        Api.create_object("Receipt", {"name": "R", "total": "5"})
    receipt = Api.create_object("Receipt", {"name": "R"})
    with pytest.raises(ValidationError):
        Api.update_object(receipt.uuid, {"total": "5"})
    # plain props still write fine alongside a computed sibling
    updated = Api.update_object(receipt.uuid, {"name": "R2"})
    assert updated.props["name"] == ScalarValueView(value="R2")


# --- rename-rewrite ---


def test_rename_array_key_rewrites_formula():
    view = receipt_type({"total": "SUM(lines.price)"})
    renamed = Api.sync_props(
        "Receipt",
        [
            (prop.uuid, "goods" if prop.key == "lines" else prop.key, PropUUID.of(prop.uuid).value_type_name(), prop.formula)
            for prop in TypeUUID.of(view.uuid).effective_props()
        ],
    )
    by_key = {prop.key: prop for prop in TypeUUID.of(renamed.uuid).effective_props()}
    assert by_key["total"].formula == "SUM(goods.price)"


def test_rename_member_key_rewrites_formula():
    receipt_type({"total": "SUM(lines.price) * 1.21"})
    item = Api.get_type("Item")
    assert item is not None
    _ = Api.sync_props(
        "Item",
        [
            (prop.uuid, "cost" if prop.key == "price" else prop.key, PropUUID.of(prop.uuid).value_type_name(), prop.formula)
            for prop in TypeUUID.of(item.uuid).effective_props()
        ],
    )
    receipt = Api.get_type("Receipt")
    assert receipt is not None
    by_key = {prop.key: prop for prop in TypeUUID.of(receipt.uuid).effective_props()}
    assert by_key["total"].formula == "(SUM(lines.cost) * 1.21)"


def test_delete_referenced_array_key_rejected():
    view = receipt_type({"total": "SUM(lines.price)"})
    draft = [(prop.uuid, prop.key, PropUUID.of(prop.uuid).value_type_name(), prop.formula) for prop in TypeUUID.of(view.uuid).effective_props()]
    with pytest.raises(ValidationError):
        Api.sync_props(
            "Receipt", [item for item in draft if item[1] != "lines"]
        )


def test_delete_referenced_member_key_rejected():
    _ = receipt_type({"total": "SUM(lines.price)"})
    item = Api.get_type("Item")
    assert item is not None
    draft = [(prop.uuid, prop.key, PropUUID.of(prop.uuid).value_type_name(), prop.formula) for prop in TypeUUID.of(item.uuid).effective_props()]
    with pytest.raises(ValidationError):
        Api.sync_props("Item", [row for row in draft if row[1] != "price"])


# --- prop-to-prop formulas with unit results (ADR-0022) ---


def _currency() -> None:
    Api.create_unit("Currency", "€")


def _receipt_item_type() -> None:
    _currency()
    Api.create_type(
        "ReceiptItem",
        {
            "price": "Numeric<Currency>",
            "quantity": "Numeric",
            "line_total": "Numeric<Currency>",
        },
        "ReceiptItems",
        embedded=True,
        formulas={"line_total": "price * quantity"},
    )


def test_prop_to_prop_with_unit_result():
    _receipt_item_type()
    _ = Api.create_type(
        "Receipt", {"name": "String", "lines": "Array<ReceiptItem>"}, "Receipts"
    )
    receipt = Api.create_object(
        "Receipt",
        {
            "name": "R1",
            "lines": [
                {"price": Quantity(Decimal(5), "€"), "quantity": Decimal(2)},
                {"price": Quantity(Decimal(3), "€"), "quantity": Decimal(4)},
            ],
        },
    )
    lines = receipt.props["lines"]
    assert isinstance(lines, ArrayValueView)
    assert lines.items is not None and len(lines.items) == 2
    first, second = lines.items
    assert isinstance(first, EmbeddedValueView) and isinstance(second, EmbeddedValueView)
    # line_total = price * quantity folds a Quantity (Currency) with a
    # Decimal (quantity) into a Quantity carrying the left unit
    assert first.props["line_total"] == ScalarValueView(value=Decimal(10), unit="€")
    assert second.props["line_total"] == ScalarValueView(value=Decimal(12), unit="€")


def test_prop_to_prop_rejects_array_sibling():
    _currency()
    _ = Api.create_type("Inner", {"name": "String"}, "Inners", embedded=True)
    with pytest.raises(ValidationError):
        Api.create_type(
            "Outer",
            {"name": "String", "items": "Array<Inner>", "total": "Numeric"},
            "Outers",
            formulas={"total": "items * 2"},
        )


def test_prop_to_prop_rejects_unknown_sibling():
    _currency()
    _ = Api.create_type("Inner", {"name": "String"}, "Inners", embedded=True)
    with pytest.raises(ValidationError):
        Api.create_type(
            "Outer",
            {"name": "String", "items": "Array<Inner>", "total": "Numeric"},
            "Outers",
            formulas={"total": "ghost * 2"},
        )


# --- aggregates over Array<Embedded> (ADR-0023) ---


def _receipt_with_lines(subtotal_formula):
    _receipt_item_type()
    _ = Api.create_type(
        "Receipt",
        {
            "name": "String",
            "lines": "Array<ReceiptItem>",
            "subtotal": "Numeric<Currency>",
        },
        "Receipts",
        formulas={"subtotal": subtotal_formula},
    )
    return Api.create_object(
        "Receipt",
        {
            "name": "R1",
            "lines": [
                {"price": Quantity(Decimal(5), "€"), "quantity": Decimal(2)},
                {"price": Quantity(Decimal(3), "€"), "quantity": Decimal(4)},
            ],
        },
    )


def test_aggregate_over_embedded_chained_and_unit():
    # SUM(lines.line_total) folds each element's computed line_total
    # (price * quantity) one level down, then sums the resulting quantities
    receipt = _receipt_with_lines("SUM(lines.line_total)")
    assert receipt.props["subtotal"] == ScalarValueView(value=Decimal(22), unit="€")


def test_aggregate_over_embedded_unit_member():
    # SUM(lines.price) over a unit-numeric member yields a Quantity, not a
    # bare magnitude (ADR-0023 unit-preserving cells)
    receipt = _receipt_with_lines("SUM(lines.price)")
    assert receipt.props["subtotal"] == ScalarValueView(value=Decimal(8), unit="€")
