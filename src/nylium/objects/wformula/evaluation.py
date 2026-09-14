"""ADR-0005 read-time evaluation: fold a formula AST over live array
rows. Unset member values count as 0 — the ADR-0005 missing-ref rule
applied to cells."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from nylium.objects.wformula.nodes import BinOp, Expr, Neg, Number

# array key -> rows; a row maps member key -> value (None = unset)
ArrayRows = Mapping[str, Sequence[Mapping[str, Decimal | None]]]


def _cell(row: Mapping[str, Decimal | None], key: str) -> Decimal:
    value = row.get(key)
    return Decimal(0) if value is None else value


def evaluate_ast(node: Expr, arrays: ArrayRows) -> Decimal:
    if isinstance(node, Number):
        return node.value
    if isinstance(node, Neg):
        return -evaluate_ast(node.operand, arrays)
    if isinstance(node, BinOp):
        left = evaluate_ast(node.left, arrays)
        right = evaluate_ast(node.right, arrays)
        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
        return left / right
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
        return sum(values, Decimal(0))
    if node.func == "AVERAGE":
        return sum(values, Decimal(0)) / Decimal(len(values))
    if node.func == "MIN":
        return min(values)
    return max(values)
