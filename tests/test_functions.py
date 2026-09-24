"""Function<T, R> props (ADR-0007 / ADR-0029): DAG creation, validation,
read-time evaluation over the owner's sibling props, instance-level prop
binding, write guard and per-owner cycle detection. Api-level; the HTTP
shape lives in test_http.py."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from nylium.api import Api, ScalarValue
from nylium.api.ApiShared import PropInput
from nylium.objects.nyfunction import NyFunction
from nylium.server.ValidationError import ValidationError


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
            "taxed": "Numeric",
        },
        "Invoices",
    )


def invoice(total="100", tax="4", amounts=None):
    _ = invoice_type()
    props: dict[str, PropInput] = {"name": "inv", "total": Decimal(total), "tax": Decimal(tax)}
    if amounts is not None:
        amount_values: list[PropInput] = [Decimal(a) for a in amounts]
        props["amounts"] = amount_values
    return Api.create_object("Invoice", props)


def passthrough():
    """Function<Invoice, Numeric> reading sibling prop `total`."""
    _ = invoice_type()
    return Api.create_function(
        "Invoice", "Numeric", "total",
        [node(uuid4(), "get_prop", 0, {"key": "total"})],
        [],
    )


# --- creation ---


def test_create_function_get_prop():
    fn = passthrough()
    assert fn.input_type == "Invoice"
    assert fn.output_type == "Numeric"
    assert fn.name == "total"
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
            "Invoice", "Numeric", "cyclic",
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
            "Invoice", "Numeric", "bad",
            [node(uuid4(), "explode", 0, {})],
            [],
        )


def test_output_type_mismatch_rejected():
    # get_prop("total") is Numeric, but the function declares String
    _ = invoice_type()
    with pytest.raises(ValidationError):
        Api.create_function(
            "Invoice", "String", "mismatch",
            [node(uuid4(), "get_prop", 0, {"key": "total"})],
            [],
        )


def test_non_scalar_output_rejected():
    # an array sink can never be a function's output (R is strictly scalar)
    _ = invoice_type()
    with pytest.raises(ValidationError):
        Api.create_function(
            "Invoice", "Array<Numeric>", "array-out",
            [node(uuid4(), "get_prop", 0, {"key": "amounts"})],
            [],
        )


def test_empty_graph_rejected():
    _ = invoice_type()
    with pytest.raises(ValidationError):
        Api.create_function("Invoice", "Numeric", "empty", [], [])


# --- evaluation (read-time, over the owner's sibling props) ---


def test_eval_get_prop():
    inv = invoice("42")
    fn = passthrough()
    assert NyFunction.evaluate_for(inv.uuid, fn.uuid) == Decimal("42")


def test_eval_mul():
    inv = invoice("100", "5")
    a, b, c = uuid4(), uuid4(), uuid4()
    fn = Api.create_function(
        "Invoice", "Numeric", "taxed",
        [
            node(a, "get_prop", 0, {"key": "total"}),
            node(b, "get_prop", 1, {"key": "tax"}),
            node(c, "mul", 2, {}),
        ],
        [edge(a, 0, c, 0), edge(b, 0, c, 1)],
    )
    assert NyFunction.evaluate_for(inv.uuid, fn.uuid) == Decimal("500")


def test_eval_div_respects_port_order():
    # total / tax: dividend is port 0, divisor port 1. The node uuids are
    # chosen so their string order is the reverse of the port order — a bug
    # that sorted inputs by uuid would flip the operands (tax/total).
    inv = invoice("100", "4")
    a = UUID("00000000-0000-0000-0000-0000000000ff")  # str(a) > str(b)
    b = UUID("00000000-0000-0000-0000-000000000001")
    c = uuid4()
    fn = Api.create_function(
        "Invoice", "Numeric", "ratio",
        [
            node(a, "get_prop", 0, {"key": "total"}),
            node(b, "get_prop", 1, {"key": "tax"}),
            node(c, "div", 2, {}),
        ],
        [edge(a, 0, c, 0), edge(b, 0, c, 1)],
    )
    assert NyFunction.evaluate_for(inv.uuid, fn.uuid) == Decimal("25")


def test_eval_sum_array():
    inv = invoice(amounts=["10", "20", "30"])
    a, b = uuid4(), uuid4()
    fn = Api.create_function(
        "Invoice", "Numeric", "sum",
        [
            node(a, "get_prop", 0, {"key": "amounts"}),
            node(b, "sum", 1, {}),
        ],
        [edge(a, 0, b, 0)],
    )
    assert NyFunction.evaluate_for(inv.uuid, fn.uuid) == Decimal("60")


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
        "Report", "Numeric", "sum-lines",
        [
            node(a, "get_prop", 0, {"key": "lines"}),
            node(b, "map", 1, {"key": "total"}),
            node(c, "sum", 2, {}),
        ],
        [edge(a, 0, b, 0), edge(b, 0, c, 0)],
    )
    assert NyFunction.evaluate_for(rep.uuid, fn.uuid) == Decimal("30")


def test_map_over_scalar_array_rejected():
    _ = invoice_type()
    a, b, c = uuid4(), uuid4(), uuid4()
    with pytest.raises(ValidationError):
        Api.create_function(
            "Invoice", "Numeric", "bad-map",
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
        "Invoice", "Numeric", "ratio",
        [
            node(a, "get_prop", 0, {"key": "total"}),
            node(b, "get_prop", 1, {"key": "tax"}),
            node(c, "div", 2, {}),
        ],
        [edge(a, 0, c, 0), edge(b, 0, c, 1)],
    )
    assert NyFunction.evaluate_for(inv.uuid, fn.uuid) is None


# --- update / delete ---


def test_update_function_replaces_graph():
    inv = invoice("7")
    fn = passthrough()
    a, b, c = uuid4(), uuid4(), uuid4()
    updated = Api.update_function(
        fn.uuid, "doubled",
        [
            node(a, "get_prop", 0, {"key": "total"}),
            node(b, "const", 1, {"value": 2}),
            node(c, "mul", 2, {}),
        ],
        [edge(a, 0, c, 0), edge(b, 0, c, 1)],
    )
    assert updated.name == "doubled"
    assert len(updated.nodes) == 3
    assert NyFunction.evaluate_for(inv.uuid, fn.uuid) == Decimal("14")


def test_delete_function():
    fn = passthrough()
    assert Api.delete_function(fn.uuid) is True
    assert Api.delete_function(fn.uuid) is False
    assert Api.get_function(fn.uuid) is None


# --- instance-level prop binding (ADR-0029) ---


def test_set_instance_prop_function_binds_and_reads():
    inv = invoice("10", "3")
    a, b, c = uuid4(), uuid4(), uuid4()
    fn = Api.create_function(
        "Invoice", "Numeric", "taxed",
        [
            node(a, "get_prop", 0, {"key": "total"}),
            node(b, "get_prop", 1, {"key": "tax"}),
            node(c, "mul", 2, {}),
        ],
        [edge(a, 0, c, 0), edge(b, 0, c, 1)],
    )
    view = Api.set_instance_prop_function(inv.uuid, "taxed", fn.uuid)
    assert view.props["taxed"] == ScalarValue(value=Decimal("30"))


def test_function_chain_recomputes_across_bindings():
    # fb -> taxed = total * tax; fa -> grand = taxed * 2. fa reads a
    # function-backed sibling, so changing total cascades through fb.
    inv = invoice("10", "3")
    a, b, c = uuid4(), uuid4(), uuid4()
    fb = Api.create_function(
        "Invoice", "Numeric", "taxed",
        [
            node(a, "get_prop", 0, {"key": "total"}),
            node(b, "get_prop", 1, {"key": "tax"}),
            node(c, "mul", 2, {}),
        ],
        [edge(a, 0, c, 0), edge(b, 0, c, 1)],
    )
    d, e, f = uuid4(), uuid4(), uuid4()
    fa = Api.create_function(
        "Invoice", "Numeric", "grand",
        [
            node(d, "get_prop", 0, {"key": "taxed"}),
            node(e, "const", 1, {"value": 2}),
            node(f, "mul", 2, {}),
        ],
        [edge(d, 0, f, 0), edge(e, 0, f, 1)],
    )
    _ = Api.set_instance_prop_function(inv.uuid, "taxed", fb.uuid)
    # fa isn't bound to a prop on Invoice, but we can evaluate the chain
    # directly: materialize_owner resolves the function-backed `taxed` via fb
    assert NyFunction.evaluate_for(inv.uuid, fa.uuid) == Decimal("60")
    # mutate total -> taxed (30 -> 12) -> grand (60 -> 24) recomputes
    _ = Api.update_object(inv.uuid, {"total": Decimal("4")})
    assert NyFunction.evaluate_for(inv.uuid, fb.uuid) == Decimal("12")
    assert NyFunction.evaluate_for(inv.uuid, fa.uuid) == Decimal("24")


def test_set_instance_prop_function_unbinds():
    inv = invoice("10", "3")
    fn = passthrough()
    _ = Api.set_instance_prop_function(inv.uuid, "taxed", fn.uuid)
    view = Api.set_instance_prop_function(inv.uuid, "taxed", None)
    assert view.props["taxed"] == ScalarValue(value=None)


def test_set_instance_prop_function_output_type_mismatch_rejected():
    inv = invoice("10", "3")
    fn = Api.create_function(
        "Invoice", "String", "label",
        [node(uuid4(), "get_prop", 0, {"key": "label"})],
        [],
    )
    with pytest.raises(ValidationError):
        Api.set_instance_prop_function(inv.uuid, "taxed", fn.uuid)


def test_set_instance_prop_function_formula_conflict_rejected():
    _ = invoice_type()
    _ = Api.create_type(
        "Report",
        {
            "name": "String",
            "amount": "Numeric",
            "subtotal": "Numeric",
            "lines": "Array<Invoice>",
        },
        "Reports",
        formulas={"amount": "SUM(lines.total)"},
    )
    # a Function<Report, Numeric> — right owner, wrong prop (formula-backed)
    fn = Api.create_function(
        "Report", "Numeric", "read-subtotal",
        [node(uuid4(), "get_prop", 0, {"key": "subtotal"})],
        [],
    )
    rep = Api.create_object("Report", {"name": "r"})
    with pytest.raises(ValidationError):
        Api.set_instance_prop_function(rep.uuid, "amount", fn.uuid)


def test_set_instance_prop_function_input_type_mismatch_rejected():
    # a Function<Invoice, Numeric> cannot bind to a Report prop — its
    # get_prop nodes read Invoice siblings, not Report siblings
    _ = invoice_type()
    _ = Api.create_type(
        "Report", {"name": "String", "amount": "Numeric"}, "Reports"
    )
    fn = passthrough()
    rep = Api.create_object("Report", {"name": "r"})
    with pytest.raises(ValidationError):
        Api.set_instance_prop_function(rep.uuid, "amount", fn.uuid)


# --- write guard ---


def test_write_guard_function_prop():
    inv = invoice("10", "3")
    fn = passthrough()
    _ = Api.set_instance_prop_function(inv.uuid, "taxed", fn.uuid)
    with pytest.raises(ValidationError):
        Api.update_object(inv.uuid, {"taxed": Decimal("5")})
    # plain props still write fine alongside a computed sibling
    updated = Api.update_object(inv.uuid, {"name": "r2"})
    assert updated.props["name"] == ScalarValue(value="r2")


# --- per-owner cross-function dependency cycle (ADR-0029) ---


def test_cross_function_dependency_cycle_rejected():
    _ = Api.create_type(
        "Node", {"name": "String", "va": "Numeric", "vb": "Numeric"}, "Nodes"
    )
    n1 = Api.create_object("Node", {"name": "n1"})
    # fa reads vb; fb reads va — on the same owner they close a cycle
    fa = Api.create_function(
        "Node", "Numeric", "fa",
        [node(uuid4(), "get_prop", 0, {"key": "vb"})],
        [],
    )
    fb = Api.create_function(
        "Node", "Numeric", "fb",
        [node(uuid4(), "get_prop", 0, {"key": "va"})],
        [],
    )
    # fb -> vb reads va, which isn't bound yet: fine
    _ = Api.set_instance_prop_function(n1.uuid, "vb", fb.uuid)
    # fa -> va reads vb (computed by fb) and fb reads va: cycle
    with pytest.raises(ValidationError):
        Api.set_instance_prop_function(n1.uuid, "va", fa.uuid)
