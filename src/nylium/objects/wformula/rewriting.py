"""ADR-0005 canonical rendering + path rewriting: render an AST back to
canonical text and rebind referenced prop keys after renames.

Pure AST walks over plain mappings — no type-graph access.
"""
from __future__ import annotations

from collections.abc import Mapping

from nylium.objects.wformula.nodes import BinOp, Call, Expr, If, Neg, Number, Ref


def render(node: Expr) -> str:
    if isinstance(node, Number):
        return str(node.value)
    if isinstance(node, Ref):
        return node.key
    if isinstance(node, Neg):
        return f"-{render(node.operand)}"
    if isinstance(node, BinOp):
        return f"({render(node.left)} {node.op} {render(node.right)})"
    if isinstance(node, If):
        return f"IF({node.prop} {node.op} {node.value}, {render(node.then)}, {render(node.else_)})"
    return f"{node.func}({'.'.join(node.path)})"


def rewrite_ast(
    node: Expr,
    array_renames: Mapping[str, str],
    member_renames: Mapping[str, Mapping[str, str]],
) -> Expr:
    if isinstance(node, Ref):
        # the owner-prop rename map rebinds sibling references (ADR-0022)
        return Ref(array_renames.get(node.key, node.key))
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
    if isinstance(node, If):
        return If(
            array_renames.get(node.prop, node.prop),
            node.op,
            node.value,
            rewrite_ast(node.then, array_renames, member_renames),
            rewrite_ast(node.else_, array_renames, member_renames),
        )
    return node
