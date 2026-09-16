"""ADR-0026: formula AST serialization — the block-editor contract."""
import pytest

from nylium.objects.wformula import Formula
from nylium.server.errors import ValidationError


def test_number_round_trip():
    assert Formula.to_dict("2") == {"kind": "number", "value": "2"}
    assert Formula.from_dict({"kind": "number", "value": "2"}) == "2"


def test_ref_and_binop():
    assert Formula.to_dict("price * 2") == {
        "kind": "binop",
        "op": "*",
        "left": {"kind": "ref", "key": "price"},
        "right": {"kind": "number", "value": "2"},
    }


def test_call_with_member_path():
    assert Formula.to_dict("SUM(lines.price)") == {
        "kind": "call",
        "func": "SUM",
        "path": ["lines", "price"],
    }


def test_call_bare_count():
    assert Formula.to_dict("COUNT(lines)") == {
        "kind": "call",
        "func": "COUNT",
        "path": ["lines"],
    }


def test_neg_round_trip():
    assert Formula.to_dict("-price") == {
        "kind": "neg",
        "operand": {"kind": "ref", "key": "price"},
    }
    assert Formula.from_dict(
        {"kind": "neg", "operand": {"kind": "ref", "key": "price"}}
    ) == "-price"


def test_if_round_trip():
    text = 'IF(kind == "tax", amount * 0.21, 0)'
    ast = Formula.to_dict(text)
    assert ast == {
        "kind": "if",
        "prop": "kind",
        "op": "==",
        "value": '"tax"',
        "then": {
            "kind": "binop",
            "op": "*",
            "left": {"kind": "ref", "key": "amount"},
            "right": {"kind": "number", "value": "0.21"},
        },
        "else": {"kind": "number", "value": "0"},
    }
    # render re-parenthesizes the binop; the AST must re-parse to itself
    rendered = Formula.from_dict(ast)
    assert rendered == 'IF(kind == "tax", (amount * 0.21), 0)'
    assert Formula.to_dict(rendered) == ast


def test_unknown_kind_rejected():
    with pytest.raises(ValidationError):
        Formula.from_dict({"kind": "wat"})


def test_bad_number_rejected():
    with pytest.raises(ValidationError):
        Formula.from_dict({"kind": "number", "value": "not-a-number"})


def test_call_needs_path():
    with pytest.raises(ValidationError):
        Formula.from_dict({"kind": "call", "func": "SUM", "path": []})


def test_missing_then_branch_rejected():
    with pytest.raises(ValidationError):
        Formula.from_dict(
            {
                "kind": "if",
                "prop": "kind",
                "op": "==",
                "value": '"tax"',
                "then": {"kind": "number", "value": "0"},
            }
        )
