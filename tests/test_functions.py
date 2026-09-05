"""Function<T, R> props (ADR-0007): DAG creation, validation, read-time
evaluation, prop binding, write guard and cycle detection. Api-level;
the HTTP shape lives in test_http.py."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from nylium.api import Api, ScalarValue
from nylium.objects.wfunction import WFunction
from nylium.server.errors import ValidationError


def node(uuid, kind, position, config):
    return (uuid, kind, position, config)


def edge(frm, frm_port, to, to_port):
    return (frm, frm_port, to, to_port)


def invoice_type():
    return Api.create_type(
        "Invoice",
        {
            "name": "String",
            "total": "Numeric",
            "tax": "Numeric",
            "label": "String",
            "amounts": "Array<Numeric>",
        },
        "Invoices",
    )


def invoice(total="100", tax="4", amounts=None):
    _ = invoice_type()
    props = {"name": "inv", "total": Decimal(total), "tax": Decimal(tax)}
    if amounts is not None:
        props["amounts"] = [Decimal(a) for a in amounts]
    return Api.create_object("Invoice", props)


def report_type():
    return Api.create_type("Report", {"name": "String", "amount": "Numeric"}, "Reports")


def passthrough(input_object_uuid=None):
    _ = invoice_type()
    return Api.create_function(
        "Invoice", "Numeric", "total", input_object_uuid,
        [node(uuid4(), "get_prop", 0, {"key": "total"})],
        [],
    )


# --- creation ---


def test_create_function_get_prop():
    fn = passthrough()
    assert fn.input_type == "Invoice"
    assert fn.output_type == "Numeric"
    assert fn.name == "total"
    assert fn.input_object_uuid is None
    assert fn.type_name == "Function<Invoice, Numeric>"
    assert len(fn.nodes) == 1
    assert fn.nodes[0].kind == "get_prop"
    assert fn.nodes[0].config == {"key": "total"}
    assert fn.edges == []


def test_list_and_get_function():
    fn = passthrough()
    assert fn.uuid in [f.uuid for f in Api.list_functions()]
    got = Api.get_function(fn.uuid)
    assert got is not None
    assert got.name == "total"


def test_get_function_non_function_is_none():
    inv = invoice()
    assert Api.get_function(inv.uuid) is None


# --- validation ---


def test_internal_cycle_rejected():
    _ = invoice_type()
    a, b = uuid4(), uuid4()
    with pytest.raises(ValidationError):
        Api.create_function(
            "Invoice", "Numeric", "cyclic", None,
            [
                node(a, "cast", 0, {"target": "Numeric"}),
                node(b, "cast", 1, {"target": "Numeric"}),
            ],
            [edge(a, 0, b, 0), edge(b, 0, a, 0)],
        )


def test_unknown_kind_rejected():
    _ = invoice_type()
    with pytest.raises(ValidationError):
        Api.create_function(
            "Invoice", "Numeric", "bad", None,
            [node(uuid4(), "explode", 0, {})],
            [],
        )


def test_output_type_mismatch_rejected():
    # get_prop("total") is Numeric, but the function declares String
    _ = invoice_type()
    with pytest.raises(ValidationError):
        Api.create_function(
            "Invoice", "String", "mismatch", None,
            [node(uuid4(), "get_prop", 0, {"key": "total"})],
            [],
        )


def test_non_scalar_output_rejected():
    # an array sink can never be a function's output (R is strictly scalar)
    _ = invoice_type()
    with pytest.raises(ValidationError):
        Api.create_function(
            "Invoice", "Array<Numeric>", "array-out", None,
            [node(uuid4(), "get_prop", 0, {"key": "amounts"})],
            [],
        )


def test_empty_graph_rejected():
    _ = invoice_type()
    with pytest.raises(ValidationError):
        Api.create_function("Invoice", "Numeric", "empty", None, [], [])


# --- evaluation (read-time) ---


def test_eval_get_prop():
    inv = invoice("42")
    fn = passthrough(inv.uuid)
    assert WFunction.evaluate_for(fn.uuid) == Decimal("42")


def test_eval_mul():
    inv = invoice("100", "5")
    a, b, c = uuid4(), uuid4(), uuid4()
    fn = Api.create_function(
        "Invoice", "Numeric", "taxed", inv.uuid,
        [
            node(a, "get_prop", 0, {"key": "total"}),
            node(b, "get_prop", 1, {"key": "tax"}),
            node(c, "mul", 2, {}),
        ],
        [edge(a, 0, c, 0), edge(b, 0, c, 1)],
    )
    assert WFunction.evaluate_for(fn.uuid) == Decimal("500")


def test_eval_div_respects_port_order():
    # total / tax: dividend is port 0, divisor port 1. The node uuids are
    # chosen so their string order is the reverse of the port order — a bug
    # that sorted inputs by uuid would flip the operands (tax/total).
    inv = invoice("100", "4")
    a = UUID("00000000-0000-0000-0000-0000000000ff")  # str(a) > str(b)
    b = UUID("00000000-0000-0000-0000-000000000001")
    c = uuid4()
    fn = Api.create_function(
        "Invoice", "Numeric", "ratio", inv.uuid,
        [
            node(a, "get_prop", 0, {"key": "total"}),
            node(b, "get_prop", 1, {"key": "tax"}),
            node(c, "div", 2, {}),
        ],
        [edge(a, 0, c, 0), edge(b, 0, c, 1)],
    )
    assert WFunction.evaluate_for(fn.uuid) == Decimal("25")


def test_eval_sum_array():
    inv = invoice(amounts=["10", "20", "30"])
    a, b = uuid4(), uuid4()
    fn = Api.create_function(
        "Invoice", "Numeric", "sum", inv.uuid,
        [
            node(a, "get_prop", 0, {"key": "amounts"}),
            node(b, "sum", 1, {}),
        ],
        [edge(a, 0, b, 0)],
    )
    assert WFunction.evaluate_for(fn.uuid) == Decimal("60")


def test_eval_map_over_object_array():
    # map reads one prop off each element of Array<Invoice>, then sum
    _ = invoice_type()
    _ = Api.create_type(
        "Report",
        {"name": "String", "lines": "Array<Invoice>"},
        "Reports",
    )
    i1 = Api.create_object("Invoice", {"name": "i1", "total": Decimal("10")})
    i2 = Api.create_object("Invoice", {"name": "i2", "total": Decimal("20")})
    rep = Api.create_object("Report", {"name": "r", "lines": [i1.uuid, i2.uuid]})
    a, b, c = uuid4(), uuid4(), uuid4()
    fn = Api.create_function(
        "Report", "Numeric", "sum-lines", rep.uuid,
        [
            node(a, "get_prop", 0, {"key": "lines"}),
            node(b, "map", 1, {"key": "total"}),
            node(c, "sum", 2, {}),
        ],
        [edge(a, 0, b, 0), edge(b, 0, c, 0)],
    )
    assert WFunction.evaluate_for(fn.uuid) == Decimal("30")


def test_map_over_scalar_array_rejected():
    _ = invoice_type()
    a, b, c = uuid4(), uuid4(), uuid4()
    with pytest.raises(ValidationError):
        Api.create_function(
            "Invoice", "Numeric", "bad-map", None,
            [
                node(a, "get_prop", 0, {"key": "amounts"}),
                node(b, "map", 1, {"key": "total"}),
                node(c, "sum", 2, {}),
            ],
            [edge(a, 0, b, 0), edge(b, 0, c, 0)],
        )


def test_eval_div_by_zero_renders_none():
    inv = invoice("100", "0")
    a, b, c = uuid4(), uuid4(), uuid4()
    fn = Api.create_function(
        "Invoice", "Numeric", "ratio", inv.uuid,
        [
            node(a, "get_prop", 0, {"key": "total"}),
            node(b, "get_prop", 1, {"key": "tax"}),
            node(c, "div", 2, {}),
        ],
        [edge(a, 0, c, 0), edge(b, 0, c, 1)],
    )
    assert WFunction.evaluate_for(fn.uuid) is None


# --- update / delete ---


def test_update_function_replaces_graph():
    inv = invoice("7")
    fn = passthrough(inv.uuid)
    a, b, c = uuid4(), uuid4(), uuid4()
    updated = Api.update_function(
        fn.uuid, "doubled", inv.uuid,
        [
            node(a, "get_prop", 0, {"key": "total"}),
            node(b, "const", 1, {"value": 2}),
            node(c, "mul", 2, {}),
        ],
        [edge(a, 0, c, 0), edge(b, 0, c, 1)],
    )
    assert updated.name == "doubled"
    assert len(updated.nodes) == 3
    assert WFunction.evaluate_for(fn.uuid) == Decimal("14")


def test_delete_function():
    fn = passthrough()
    assert Api.delete_function(fn.uuid) is True
    assert Api.delete_function(fn.uuid) is False
    assert Api.get_function(fn.uuid) is None


# --- prop binding ---


def test_set_prop_function_binds_and_reads():
    _ = report_type()
    inv = invoice("10", "3")
    a, b, c = uuid4(), uuid4(), uuid4()
    fn = Api.create_function(
        "Invoice", "Numeric", "taxed", inv.uuid,
        [
            node(a, "get_prop", 0, {"key": "total"}),
            node(b, "get_prop", 1, {"key": "tax"}),
            node(c, "mul", 2, {}),
        ],
        [edge(a, 0, c, 0), edge(b, 0, c, 1)],
    )
    type_view = Api.set_prop_function("Report", "amount", fn.uuid)
    by_key = {p.key: p for p in type_view.props}
    assert by_key["amount"].function_uuid == fn.uuid
    rep = Api.create_object("Report", {"name": "r1"})
    view = Api.get_object(rep.uuid)
    assert view is not None
    assert view.props["amount"] == ScalarValue(value=Decimal("30"))


def test_set_prop_function_unbinds():
    _ = report_type()
    fn = passthrough()
    _ = Api.set_prop_function("Report", "amount", fn.uuid)
    type_view = Api.set_prop_function("Report", "amount", None)
    by_key = {p.key: p for p in type_view.props}
    assert by_key["amount"].function_uuid is None


def test_set_prop_function_output_type_mismatch_rejected():
    _ = invoice_type()
    _ = report_type()
    fn = Api.create_function(
        "Invoice", "String", "label", None,
        [node(uuid4(), "get_prop", 0, {"key": "label"})],
        [],
    )
    with pytest.raises(ValidationError):
        Api.set_prop_function("Report", "amount", fn.uuid)


def test_set_prop_function_formula_conflict_rejected():
    _ = invoice_type()
    _ = Api.create_type(
        "Report",
        {"name": "String", "amount": "Numeric", "items": "Array<Invoice>"},
        "Reports",
        formulas={"amount": "SUM(items.total)"},
    )
    fn = passthrough()
    with pytest.raises(ValidationError):
        Api.set_prop_function("Report", "amount", fn.uuid)


# --- write guard ---


def test_write_guard_function_prop():
    _ = report_type()
    fn = passthrough()
    _ = Api.set_prop_function("Report", "amount", fn.uuid)
    with pytest.raises(ValidationError):
        Api.create_object("Report", {"name": "r", "amount": Decimal("5")})
    rep = Api.create_object("Report", {"name": "r"})
    with pytest.raises(ValidationError):
        Api.update_object(rep.uuid, {"amount": Decimal("5")})
    # plain props still write fine alongside a computed sibling
    updated = Api.update_object(rep.uuid, {"name": "r2"})
    assert updated.props["name"] == ScalarValue(value="r2")


# --- cross-function dependency cycle ---


def test_cross_function_dependency_cycle_rejected():
    _ = Api.create_type("Alpha", {"name": "String", "computed": "Numeric"}, "Alphas")
    _ = Api.create_type("Beta", {"name": "String", "computed": "Numeric"}, "Betas")
    a1 = Api.create_object("Alpha", {"name": "a1"})
    b1 = Api.create_object("Beta", {"name": "b1"})
    fa = Api.create_function(
        "Beta", "Numeric", "fa", b1.uuid,
        [node(uuid4(), "get_prop", 0, {"key": "computed"})],
        [],
    )
    fb = Api.create_function(
        "Alpha", "Numeric", "fb", a1.uuid,
        [node(uuid4(), "get_prop", 0, {"key": "computed"})],
        [],
    )
    # FB -> Beta.computed is fine on its own: FB reads Alpha, which isn't
    # bound yet
    _ = Api.set_prop_function("Beta", "computed", fb.uuid)
    # FA -> Alpha.computed closes the loop: FA reads Beta (computed by FB)
    # and FB reads Alpha (computed by FA)
    with pytest.raises(ValidationError):
        Api.set_prop_function("Alpha", "computed", fa.uuid)
