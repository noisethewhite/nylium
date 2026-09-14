"""ADR-0005 canonical rendering + path rewriting: render an AST back to
canonical text and rebind referenced prop keys after renames.

Pure AST walks over plain mappings — no type-graph access.
"""
from __future__ import annotations

from collections.abc import Mapping

from nylium.objects.wformula.nodes import BinOp, Call, Expr, Neg, Number


def render(node: Expr) -> str:
    if isinstance(node, Number):
        return str(node.value)
    if isinstance(node, Neg):
        return f"-{render(node.operand)}"
    if isinstance(node, BinOp):
        return f"({render(node.left)} {node.op} {render(node.right)})"
    return f"{node.func}({'.'.join(node.path)})"


def rewrite_ast(
    node: Expr,
    array_renames: Mapping[str, str],
    member_renames: Mapping[str, Mapping[str, str]],
) -> Expr:
    if isinstance(node, Call):
        array_key = array_renames.get(node.path[0], node.path[0])
        if len(node.path) == 1:
            return Call(node.func, (array_key,))
        member = member_renames.get(node.path[0], {}).get(node.path[1], node.path[1])
        return Call(node.func, (array_key, member))
    if isinstance(node, BinOp):
        return BinOp(
            node.op,
            rewrite_ast(node.left, array_renames, member_renames),
            rewrite_ast(node.right, array_renames, member_renames),
        )
    if isinstance(node, Neg):
        return Neg(rewrite_ast(node.operand, array_renames, member_renames))
    return node
