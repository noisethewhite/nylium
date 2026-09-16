"""Collect props (ADR-0025): derived Array<T> over an ordered scalar range.

A collect prop derives its members at read time with one reverse range query
on the target type's member prop, bounded by the owner's from/to siblings.
`total = SUM(expenses.amount)` folds that derived array through ADR-0023.
"""

from datetime import date
from decimal import Decimal

import pytest

from nylium.api import Api, ArrayValue, RefValue, ScalarValue
from nylium.server.errors import ValidationError


def expense_type():
    return Api.create_type(
        "Expense", {"name": "String", "date": "Date", "amount": "Numeric"}, "Expenses"
    )


def period_type(collects=None, formulas=None):
    expense_type()
    return Api.create_type(
        "Period",
        {
            "name": "String",
            "from": "Date",
            "to": "Date",
            "expenses": "Array<Expense>",
            "total": "Numeric",
        },
        "Periods",
        collects=collects,
        formulas=formulas,
    )


def _expense(name, day, amount):
    expense_type()
    return Api.create_object(
        "Expense",
        {"name": name, "date": date(2026, 9, day), "amount": Decimal(amount)},
    )


# --- read-time derivation ---


def test_collect_derives_range_and_total():
    period_type({"expenses": "date"}, {"total": "SUM(expenses.amount)"})
    e1 = _expense("a", 10, "10")
    e2 = _expense("b", 15, "20")
    e3 = _expense("c", 20, "30")
    period = Api.create_object(
        "Period", {"name": "P", "from": date(2026, 9, 12), "to": date(2026, 9, 16)}
    )
    expenses = period.props["expenses"]
    assert isinstance(expenses, ArrayValue)
    assert expenses.items is not None
    # only e2 (the 15th) falls inside [12, 16]
    refs = [
        item.ref.uuid
        for item in expenses.items
        if isinstance(item, RefValue) and item.ref is not None
    ]
    assert refs == [e2.uuid]
    assert period.props["total"] == ScalarValue(value=Decimal(20))


def test_collect_empty_range_aggregates_zero():
    period_type({"expenses": "date"}, {"total": "SUM(expenses.amount)"})
    _expense("a", 10, "10")
    period = Api.create_object(
        "Period", {"name": "P", "from": date(2026, 9, 20), "to": date(2026, 9, 30)}
    )
    expenses = period.props["expenses"]
    assert isinstance(expenses, ArrayValue)
    assert expenses.items == []
    assert period.props["total"] == ScalarValue(value=Decimal(0))


def test_collect_inclusive_bounds():
    period_type({"expenses": "date"})
    e1 = _expense("a", 12, "1")
    e2 = _expense("b", 16, "2")
    period = Api.create_object(
        "Period", {"name": "P", "from": date(2026, 9, 12), "to": date(2026, 9, 16)}
    )
    expenses = period.props["expenses"]
    assert isinstance(expenses, ArrayValue)
    assert expenses.items is not None
    # between is inclusive on both ends
    refs = {
        item.ref.uuid
        for item in expenses.items
        if isinstance(item, RefValue) and item.ref is not None
    }
    assert refs == {e1.uuid, e2.uuid}


# --- schema validation ---


def test_collect_must_be_array():
    expense_type()
    with pytest.raises(ValidationError):
        Api.create_type(
            "Bad",
            {"name": "String", "from": "Date", "to": "Date", "expenses": "Expense"},
            "Bads",
            collects={"expenses": "date"},
        )


def test_collect_member_must_exist():
    with pytest.raises(ValidationError):
        period_type({"expenses": "ghost"})


def test_collect_member_must_be_ordered_scalar():
    # "name" is a String — not an ordered scalar
    with pytest.raises(ValidationError):
        period_type({"expenses": "name"})


def test_collect_requires_both_bounds():
    expense_type()
    with pytest.raises(ValidationError):
        Api.create_type(
            "Period",
            {"name": "String", "from": "Date", "expenses": "Array<Expense>"},
            "Periods",
            collects={"expenses": "date"},
        )


def test_collect_bounds_must_match_member_type():
    expense_type()
    with pytest.raises(ValidationError):
        Api.create_type(
            "Period",
            {
                "name": "String",
                "from": "Date",
                "to": "Numeric",
                "expenses": "Array<Expense>",
            },
            "Periods",
            collects={"expenses": "date"},
        )


def test_collect_rejects_embedded_target():
    Api.create_type("Line", {"name": "String", "qty": "Numeric"}, "Lines", embedded=True)
    with pytest.raises(ValidationError):
        Api.create_type(
            "Period",
            {"name": "String", "from": "Numeric", "to": "Numeric", "lines": "Array<Line>"},
            "Periods",
            collects={"lines": "qty"},
        )


def test_collect_and_formula_mutually_exclusive():
    with pytest.raises(ValidationError):
        period_type({"expenses": "date"}, {"expenses": "SUM(expenses.amount)"})


# --- the write guard ---


def test_collect_prop_is_readonly():
    period_type({"expenses": "date"})
    with pytest.raises(ValidationError):
        Api.create_object(
            "Period",
            {
                "name": "P",
                "from": date(2026, 9, 1),
                "to": date(2026, 9, 30),
                "expenses": [],
            },
        )
