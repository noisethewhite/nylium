"""ADR-0005/0022/0023 read-time evaluation: fold a formula AST over live
array rows and the owner's sibling prop values. Unset member and sibling
values count as 0 — the ADR-0005 missing-ref rule applied to cells.
Arithmetic promotes to a Quantity whenever either operand is a Quantity,
carrying the source part name through; array aggregates over unit-numeric
members likewise produce a Quantity (ADR-0023)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation

from nylium.objects.quantity import Quantity
from nylium.objects.wformula.nodes import BinOp, Expr, If, Neg, Number, Ref

# array key -> rows; a row maps member key -> value (None = unset)
ArrayRows = Mapping[str, Sequence[Mapping[str, "Value | None"]]]
# sibling prop key -> stored scalar (None = unset); a Quantity stays a
# Quantity so unit promotion can recover the entered part name, and a
# String/enum stays a str so an IF cond can compare it
SiblingRow = Mapping[str, Decimal | Quantity | str | None]

Value = Decimal | Quantity


def _cell(row: Mapping[str, "Value | None"], key: str) -> Value:
    value = row.get(key)
    return Decimal(0) if value is None else value


def _magnitude(value: Value) -> Decimal:
    return value.value if isinstance(value, Quantity) else value


def _sum(values: Sequence[Value]) -> Value:
    """Aggregate SUM. A quantity cell promotes the total to a Quantity in
    the first quantity's part (members share one type, so parts agree)."""
    part = next((v.unit for v in values if isinstance(v, Quantity)), None)
    total = sum((_magnitude(v) for v in values), Decimal(0))
    return Quantity(total, part) if part is not None else total


def _average(values: Sequence[Value]) -> Value:
    total = _sum(values)
    count = Decimal(len(values))
    if isinstance(total, Quantity):
        return Quantity(total.value / count, total.unit)
    return total / count


def _apply(op: str, left: Decimal, right: Decimal) -> Decimal:
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    return left / right


def _binop(op: str, left: Value, right: Value) -> Value:
    """Fold two operands; if either is a Quantity the result is too, with
    the part name taken from the left Quantity when both are quantities."""
    if isinstance(left, Quantity):
        rvalue = right.value if isinstance(right, Quantity) else right
        return Quantity(_apply(op, left.value, rvalue), left.unit)
    if isinstance(right, Quantity):
        return Quantity(_apply(op, left, right.value), right.unit)
    return _apply(op, left, right)


def _compare(actual: Decimal | Quantity | str | None, op: str, value_str: str) -> bool:
    """ADR-0024 cond: an unset value is not equal; a number compares
    numerically against the literal; anything else (a String/enum) compares
    as text against the literal with its quotes stripped."""
    if actual is None:
        equal = False
    elif isinstance(actual, (Decimal, int)):
        try:
            equal = actual == Decimal(value_str)
        except InvalidOperation:
            equal = False
    else:
        equal = str(actual) == value_str.strip("\"'")
    return equal if op == "==" else not equal


def evaluate_ast(node: Expr, arrays: ArrayRows, scalars: SiblingRow) -> Value:
    if isinstance(node, Number):
        return node.value
    if isinstance(node, Ref):
        value = scalars.get(node.key)
        # a Ref names a numeric sibling (validation rejects the rest), so
        # any str in the mapping belongs to a cond prop, never here
        return Decimal(0) if value is None or isinstance(value, str) else value
    if isinstance(node, Neg):
        inner = evaluate_ast(node.operand, arrays, scalars)
        if isinstance(inner, Quantity):
            return Quantity(-inner.value, inner.unit)
        return -inner
    if isinstance(node, BinOp):
        left = evaluate_ast(node.left, arrays, scalars)
        right = evaluate_ast(node.right, arrays, scalars)
        return _binop(node.op, left, right)
    if isinstance(node, If):
        if _compare(scalars.get(node.prop), node.op, node.value):
            return evaluate_ast(node.then, arrays, scalars)
        return evaluate_ast(node.else_, arrays, scalars)
    rows = arrays.get(node.path[0], ())
    if node.func == "COUNT":
        if len(node.path) == 1:
            # a bare COUNT counts stored rows, dangling refs included
            return Decimal(len(rows))
        return Decimal(sum(1 for row in rows if row.get(node.path[1]) is not None))
    values = [_cell(row, node.path[1]) for row in rows]
    if not values:
        return Decimal(0)
    if node.func == "SUM":
        return _sum(values)
    if node.func == "AVERAGE":
        return _average(values)
    if node.func == "MIN":
        return min(values, key=_magnitude)
    return max(values, key=_magnitude)
