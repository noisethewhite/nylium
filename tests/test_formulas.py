"""Formula props (ADR-0005): storage, grammar and schema validation.

Formulas are validated at type-write time (create_type / sync_props);
read-time evaluation is a later slice and not covered here. Api-level;
HTTP shape lives in test_http.py."""

import pytest
from uuid import UUID

from nylium.api import Api
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
            "items": "Array<Item>",
            "total": "Numeric",
            "count": "Integer",
        },
        "Receipts",
        formulas=formulas,
    )


def test_valid_formulas_stored_and_visible():
    view = receipt_type(
        {"total": "SUM(items.price) * 1.21", "count": "COUNT(items)"}
    )
    by_key = {prop.key: prop for prop in view.props}
    assert by_key["total"].formula == "SUM(items.price) * 1.21"
    assert by_key["count"].formula == "COUNT(items)"
    # plain stored props default to None
    assert by_key["name"].formula is None
    assert by_key["items"].formula is None


def test_unknown_function_rejected():
    with pytest.raises(ValidationError):
        receipt_type({"total": "MEDIAN(items.price)"})


def test_unknown_array_key_rejected():
    with pytest.raises(ValidationError):
        receipt_type({"total": "SUM(stuff.price)"})


def test_non_array_key_rejected():
    with pytest.raises(ValidationError):
        receipt_type({"total": "SUM(name.price)"})


def test_unknown_member_prop_rejected():
    with pytest.raises(ValidationError):
        receipt_type({"total": "SUM(items.weight)"})


def test_non_numeric_member_prop_rejected():
    with pytest.raises(ValidationError):
        receipt_type({"total": "SUM(items.label)"})


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
            formulas={"total": "SUM(items.price)"},
        )


def test_integer_formula_must_be_bare_count():
    with pytest.raises(ValidationError):
        receipt_type({"count": "SUM(items.price)"})
    with pytest.raises(ValidationError):
        receipt_type({"count": "COUNT(items.price)"})
    # ...while a Numeric prop may hold a bare COUNT too
    view = receipt_type({"total": "COUNT(items)"})
    by_key = {prop.key: prop for prop in view.props}
    assert by_key["total"].formula == "COUNT(items)"


def test_formula_keys_must_name_props():
    with pytest.raises(ValidationError):
        receipt_type({"ghost": "SUM(items.price)"})


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
        "Receipt", _sync_items(view, {"total": "SUM(items.price)"})
    )
    by_key = {prop.key: prop for prop in synced.props}
    assert by_key["total"].formula == "SUM(items.price)"

    synced = Api.sync_props(
        "Receipt", _sync_items(synced, {"total": "MAX(items.price) + 1"})
    )
    by_key = {prop.key: prop for prop in synced.props}
    assert by_key["total"].formula == "MAX(items.price) + 1"

    synced = Api.sync_props("Receipt", _sync_items(synced, {}))
    by_key = {prop.key: prop for prop in synced.props}
    assert by_key["total"].formula is None


def test_sync_props_validates_formula():
    view = receipt_type()
    with pytest.raises(ValidationError):
        Api.sync_props("Receipt", _sync_items(view, {"total": "SUM(items.nope)"}))
