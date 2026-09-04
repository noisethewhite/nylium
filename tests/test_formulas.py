"""Formula props (ADR-0005): storage, grammar, schema validation,
read-time evaluation, the write guard and rename-rewrite.

Api-level; HTTP shape lives in test_http.py."""

from decimal import Decimal

import pytest
from uuid import UUID

from nylium.api import Api, ScalarValue
from nylium.server.errors import ValidationError


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
    by_key = {prop.key: prop for prop in view.props}
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
    by_key = {prop.key: prop for prop in view.props}
    assert by_key["total"].formula == "COUNT(lines)"


def test_formula_keys_must_name_props():
    with pytest.raises(ValidationError):
        receipt_type({"ghost": "SUM(lines.price)"})


def _sync_items(
    view, formulas
) -> list[tuple[UUID | None, str, str, str | None]]:
    return [
        (prop.uuid, prop.key, prop.value_type, formulas.get(prop.key))
        for prop in view.props
    ]


def test_sync_props_sets_updates_and_clears_formula():
    view = receipt_type()
    by_key = {prop.key: prop for prop in view.props}
    assert by_key["total"].formula is None

    synced = Api.sync_props(
        "Receipt", _sync_items(view, {"total": "SUM(lines.price)"})
    )
    by_key = {prop.key: prop for prop in synced.props}
    assert by_key["total"].formula == "SUM(lines.price)"

    synced = Api.sync_props(
        "Receipt", _sync_items(synced, {"total": "MAX(lines.price) + 1"})
    )
    by_key = {prop.key: prop for prop in synced.props}
    assert by_key["total"].formula == "MAX(lines.price) + 1"

    synced = Api.sync_props("Receipt", _sync_items(synced, {}))
    by_key = {prop.key: prop for prop in synced.props}
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
    assert view.props["total"] == ScalarValue(value=Decimal("12.5"))


def test_eval_arithmetic_and_integer_count():
    receipt = _receipt(
        {"total": "SUM(lines.price) * 1.21", "count": "COUNT(lines)"},
        [("a", "100"), ("b", "0")],
    )
    view = Api.get_object(receipt.uuid)
    assert view is not None
    assert view.props["total"] == ScalarValue(value=Decimal("121.00"))
    # a bare COUNT on an Integer prop yields a plain int
    assert view.props["count"] == ScalarValue(value=2)


def test_eval_unset_member_counts_zero():
    # COUNT with a member path is only legal on a Numeric prop, so fold it
    # into the total: SUM(10) + COUNT(set cells) = 11
    receipt = _receipt(
        {"total": "SUM(lines.price) + COUNT(lines.price)"},
        [("a", "10"), ("b", None)],
    )
    view = Api.get_object(receipt.uuid)
    assert view is not None
    assert view.props["total"] == ScalarValue(value=Decimal("11"))


def test_eval_avg_min_max():
    receipt = _receipt(
        {"total": "AVERAGE(lines.price) + MIN(lines.price) + MAX(lines.price)"},
        [("a", "10"), ("b", "20"), ("c", "30")],
    )
    view = Api.get_object(receipt.uuid)
    assert view is not None
    assert view.props["total"] == ScalarValue(value=Decimal("60"))


def test_eval_empty_array_aggregates_zero():
    receipt = _receipt({"total": "SUM(lines.price)", "count": "COUNT(lines)"}, [])
    view = Api.get_object(receipt.uuid)
    assert view is not None
    assert view.props["total"] == ScalarValue(value=Decimal("0"))
    assert view.props["count"] == ScalarValue(value=0)


def test_eval_division_by_zero_renders_empty():
    receipt = _receipt({"total": "SUM(lines.price) / COUNT(lines.price)"}, [])
    view = Api.get_object(receipt.uuid)
    assert view is not None
    assert view.props["total"] == ScalarValue(value=None)


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
    assert view.props["total"] == ScalarValue(value=Decimal("10"))
    assert view.props["count"] == ScalarValue(value=1)


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
    assert updated.props["name"] == ScalarValue(value="R2")


# --- rename-rewrite ---


def test_rename_array_key_rewrites_formula():
    view = receipt_type({"total": "SUM(lines.price)"})
    renamed = Api.sync_props(
        "Receipt",
        [
            (prop.uuid, "goods" if prop.key == "lines" else prop.key, prop.value_type, prop.formula)
            for prop in view.props
        ],
    )
    by_key = {prop.key: prop for prop in renamed.props}
    assert by_key["total"].formula == "SUM(goods.price)"


def test_rename_member_key_rewrites_formula():
    view = receipt_type({"total": "SUM(lines.price) * 1.21"})
    item = Api.get_type("Item")
    _ = Api.sync_props(
        "Item",
        [
            (prop.uuid, "cost" if prop.key == "price" else prop.key, prop.value_type, prop.formula)
            for prop in item.props
        ],
    )
    receipt = Api.get_type("Receipt")
    by_key = {prop.key: prop for prop in receipt.props}
    assert by_key["total"].formula == "(SUM(lines.cost) * 1.21)"


def test_delete_referenced_array_key_rejected():
    view = receipt_type({"total": "SUM(lines.price)"})
    draft = [(prop.uuid, prop.key, prop.value_type, prop.formula) for prop in view.props]
    with pytest.raises(ValidationError):
        Api.sync_props(
            "Receipt", [item for item in draft if item[1] != "lines"]
        )


def test_delete_referenced_member_key_rejected():
    _ = receipt_type({"total": "SUM(lines.price)"})
    item = Api.get_type("Item")
    draft = [(prop.uuid, prop.key, prop.value_type, prop.formula) for prop in item.props]
    with pytest.raises(ValidationError):
        Api.sync_props("Item", [row for row in draft if row[1] != "price"])
