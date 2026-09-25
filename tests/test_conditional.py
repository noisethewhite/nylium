"""Conditional formula expressions (ADR-0024): ``IF(<prop> <op> <lit>, <then>,
<else>)`` — parsing, schema validation, and read-time evaluation over enum
and numeric cond props.

Api-level; HTTP shape lives in test_http.py."""

from decimal import Decimal

import pytest

from nylium.api import Api, ScalarValueView
from nylium.api.ApiShared import PropInput
from nylium.data.types.Quantity import Quantity
from nylium.server.ValidationError import ValidationError


def _fee_kind():
    return Api.create_enum("FeeKind", ["tax", "discount"])


def _fee_type(formulas):
    _fee_kind()
    Api.create_unit("Currency", "€")
    return Api.create_type(
        "Fee",
        {
            "name": "String",
            "kind": "FeeKind",
            "basis": "Numeric<Currency>",
            "rate": "Numeric",
            "effective": "Numeric<Currency>",
        },
        "Fees",
        formulas=formulas,
    )


def _fee(kind, basis="100", rate="0.21"):
    props: dict[str, PropInput] = {
        "name": "f",
        "basis": Quantity(Decimal(basis), "€"),
        "rate": Decimal(rate),
    }
    if kind is not None:
        props["kind"] = kind
    return Api.create_object("Fee", props)


def test_if_enum_tax_and_discount_branches():
    _fee_type({"effective": 'IF(kind == "tax", basis * rate, -basis * rate)'})
    tax = _fee("tax")
    assert tax.props["effective"] == ScalarValueView(value=Decimal("21.00"), unit="€")
    discount = _fee("discount")
    assert discount.props["effective"] == ScalarValueView(
        value=Decimal("-21.00"), unit="€"
    )


def test_if_not_equal_operator():
    _fee_type({"effective": 'IF(kind != "tax", -basis * rate, basis * rate)'})
    # discount -> then (negative); tax -> else (positive)
    discount = _fee("discount", rate="0.10")
    assert discount.props["effective"] == ScalarValueView(
        value=Decimal("-10.00"), unit="€"
    )
    tax = _fee("tax", rate="0.10")
    assert tax.props["effective"] == ScalarValueView(value=Decimal("10.00"), unit="€")


def test_if_unset_cond_falls_to_else():
    _fee_type({"effective": 'IF(kind == "tax", basis * rate, -basis * rate)'})
    fee = _fee(None, rate="0.10")
    assert fee.props["effective"] == ScalarValueView(value=Decimal("-10.00"), unit="€")


def test_if_numeric_cond():
    Api.create_type(
        "Item",
        {"name": "String", "qty": "Integer", "price": "Numeric", "total": "Numeric"},
        "Items",
        formulas={"total": "IF(qty == 2, price, price * 2)"},
    )
    match = Api.create_object("Item", {"name": "x", "qty": 2, "price": Decimal(10)})
    assert match.props["total"] == ScalarValueView(value=Decimal(10))
    miss = Api.create_object("Item", {"name": "y", "qty": 3, "price": Decimal(10)})
    assert miss.props["total"] == ScalarValueView(value=Decimal(20))


# --- validation ---


def test_if_unknown_cond_prop_rejected():
    with pytest.raises(ValidationError):
        _fee_type({"effective": 'IF(ghost == "tax", basis * rate, -basis * rate)'})


def test_if_array_cond_prop_rejected():
    with pytest.raises(ValidationError):
        Api.create_type(
            "Bad",
            {"name": "String", "tags": "Array<String>", "total": "Numeric"},
            "Bads",
            formulas={"total": 'IF(tags == "tax", 1, 2)'},
        )


def test_if_string_literal_on_numeric_cond_rejected():
    with pytest.raises(ValidationError):
        _fee_type({"effective": 'IF(rate == "tax", basis * rate, -basis * rate)'})


def test_if_number_literal_on_string_cond_rejected():
    with pytest.raises(ValidationError):
        _fee_type({"effective": "IF(kind == 2, basis * rate, -basis * rate)"})


def test_if_malformed_cond_rejected():
    with pytest.raises(ValidationError):
        _fee_type({"effective": "IF(kind tax, basis * rate, -basis * rate)"})
