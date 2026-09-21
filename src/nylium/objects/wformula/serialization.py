"""ADR-0026: JSON serialization of the formula AST — the shared contract
between the block editor (frontend) and the parser/render (backend).

Pure structural walks: the frontend renders blocks from this JSON and sends it
back to be re-rendered to canonical text. Validation of *what the AST means*
(referenced props exist, are numeric, etc.) stays on the save path; here we
only reject structurally invalid nodes.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TypeAlias, cast

from nylium.objects.wformula.nodes import BinOp, Call, Expr, If, Neg, Number, Ref
from nylium.server.errors import ValidationError

# The wire shape of a formula AST node (ADR-0026). Values are `str` for
# literals/ops/keys, `list` for a Call path, or a nested `AstNode`.
AstNode: TypeAlias = dict[str, object]


def _invalid(message: str) -> Exception:

    return ValidationError(message)


def _string(data: AstNode, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise _invalid(f"formula AST field {key!r} must be a string")
    return value


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise _invalid(f"formula number literal {value!r} is not a decimal") from None


def ast_to_dict(node: Expr) -> AstNode:
    if isinstance(node, Number):
        return {"kind": "number", "value": str(node.value)}
    if isinstance(node, Ref):
        return {"kind": "ref", "key": node.key}
    if isinstance(node, BinOp):
        return {
            "kind": "binop",
            "op": node.op,
            "left": ast_to_dict(node.left),
            "right": ast_to_dict(node.right),
        }
    if isinstance(node, Neg):
        return {"kind": "neg", "operand": ast_to_dict(node.operand)}
    if isinstance(node, Call):
        return {"kind": "call", "func": node.func, "path": list(node.path)}
    # the only remaining Expr is the conditional (ADR-0024)
    return {
        "kind": "if",
        "prop": node.prop,
        "op": node.op,
        "value": node.value,
        "then": ast_to_dict(node.then),
        "else": ast_to_dict(node.else_),
    }


def dict_to_ast(data: object) -> Expr:
    if not isinstance(data, dict):
        raise _invalid("formula AST node must be an object")
    node = cast(AstNode, data)
    kind = node.get("kind")
    if kind == "number":
        return Number(_decimal(node.get("value")))
    if kind == "ref":
        return Ref(_string(node, "key"))
    if kind == "binop":
        return BinOp(
            _string(node, "op"),
            dict_to_ast(node.get("left")),
            dict_to_ast(node.get("right")),
        )
    if kind == "neg":
        return Neg(dict_to_ast(node.get("operand")))
    if kind == "call":
        path = node.get("path")
        if not isinstance(path, list):
            raise _invalid("call node needs a non-empty path list")
        parts = cast(list[object], path)
        if len(parts) == 0:
            raise _invalid("call node needs a non-empty path list")
        return Call(_string(node, "func"), tuple(str(part) for part in parts))
    if kind == "if":
        return If(
            _string(node, "prop"),
            _string(node, "op"),
            _string(node, "value"),
            dict_to_ast(node.get("then")),
            dict_to_ast(node.get("else")),
        )
    raise _invalid(f"unknown formula AST node kind {kind!r}")
