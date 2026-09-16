"""ADR-0005/0022/0023 read-time evaluation: fold a formula AST over live
array rows and the owner's sibling prop values. Unset member and sibling
values count as 0 — the ADR-0005 missing-ref rule applied to cells.
Arithmetic promotes to a Quantity whenever either operand is a Quantity,
carrying the source part name through; array aggregates over unit-numeric
members likewise produce a Quantity (ADR-0023)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from nylium.objects.quantity import Quantity
from nylium.objects.wformula.nodes import BinOp, Expr, Neg, Number, Ref

# array key -> rows; a row maps member key -> value (None = unset)
ArrayRows = Mapping[str, Sequence[Mapping[str, "Value | None"]]]
# sibling prop key -> stored scalar (None = unset); a Quantity stays a
# Quantity so unit promotion can recover the entered part name
SiblingRow = Mapping[str, Decimal | Quantity | None]

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


def evaluate_ast(node: Expr, arrays: ArrayRows, scalars: SiblingRow) -> Value:
    if isinstance(node, Number):
        return node.value
    if isinstance(node, Ref):
        value = scalars.get(node.key)
        return Decimal(0) if value is None else value
    if isinstance(node, Neg):
        inner = evaluate_ast(node.operand, arrays, scalars)
        if isinstance(inner, Quantity):
            return Quantity(-inner.value, inner.unit)
        return -inner
    if isinstance(node, BinOp):
        left = evaluate_ast(node.left, arrays, scalars)
        right = evaluate_ast(node.right, arrays, scalars)
        return _binop(node.op, left, right)
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
