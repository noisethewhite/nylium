"""Formula (ADR-0005): the static surface over the formula language —
parse + schema validation + evaluation + rename rewriting.

The class takes only plain data (prop schemas as ``(key, type_name)``
pairs and a member-type resolver), so it stays free of any object-layer
coupling; the syntax lives in ``parsing``, the AST in ``nodes``,
read-time folding in ``evaluation``, canonical rendering in
``rewriting``.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import ClassVar

from nylium.objects.wformula.evaluation import evaluate_ast
from nylium.objects.wformula.nodes import FUNCTIONS, BinOp, Call, Expr, If, Neg, Ref
from nylium.objects.wformula.parsing import Parser, tokenize
from nylium.objects.wformula.rewriting import render, rewrite_ast
from nylium.objects.quantity import Quantity
from nylium.objects.wscalar import WInteger, WNumeric, WString
from nylium.objects.wtype import WType


def _calls(node: Expr) -> Iterator[Call]:
    """Every Call node in the AST, depth-first (into IF branches too)."""
    if isinstance(node, Call):
        yield node
    elif isinstance(node, BinOp):
        yield from _calls(node.left)
        yield from _calls(node.right)
    elif isinstance(node, Neg):
        yield from _calls(node.operand)
    elif isinstance(node, If):
        yield from _calls(node.then)
        yield from _calls(node.else_)


def _refs(node: Expr) -> Iterator[Ref]:
    """Every Ref node in the AST, depth-first (into IF branches too)."""
    if isinstance(node, Ref):
        yield node
    elif isinstance(node, BinOp):
        yield from _refs(node.left)
        yield from _refs(node.right)
    elif isinstance(node, Neg):
        yield from _refs(node.operand)
    elif isinstance(node, If):
        yield from _refs(node.then)
        yield from _refs(node.else_)


def _ifs(node: Expr) -> Iterator[If]:
    """Every IF conditional in the AST, depth-first (nested included)."""
    if isinstance(node, If):
        yield node
        yield from _ifs(node.then)
        yield from _ifs(node.else_)
    elif isinstance(node, BinOp):
        yield from _ifs(node.left)
        yield from _ifs(node.right)
    elif isinstance(node, Neg):
        yield from _ifs(node.operand)


def _is_string_literal(value: str) -> bool:
    """A cond literal written quoted (a string/enum constant), vs a bare number."""
    return value.startswith('"') or value.startswith("'")


def _is_numeric(type_name: str) -> bool:
    """Integer or Decimal, including the unit-parameterized Numeric<Unit>."""
    if type_name == WInteger.TYPE_NAME:
        return True
    if type_name == WNumeric.TYPE_NAME:
        return True
    return type_name.startswith(WNumeric.TYPE_NAME + "<") and type_name.endswith(">")


class Formula:
    """ADR-0005 formula surface: parse + static schema validation.

    ``owner_type_props`` is the owner type's full prop schema as
    ``(key, value_type_name)`` pairs; ``resolve_member_type`` returns the
    schema of an array's element type (or None when it cannot). Both are
    plain data, so this class stays free of any object-layer coupling.
    """

    FUNCTIONS: ClassVar[frozenset[str]] = FUNCTIONS

    @classmethod
    def parse(cls, formula: str) -> Expr:
        return Parser(tokenize(formula)).parse()

    @classmethod
    def is_bare_count(cls, formula: str) -> bool:
        """True when the formula is exactly ``COUNT(<array>)`` — the only
        shape an Integer formula prop may take."""
        ast = cls.parse(formula)
        return isinstance(ast, Call) and ast.func == "COUNT" and len(ast.path) == 1

    @classmethod
    def validate(
        cls,
        formula: str,
        owner_type_props: Sequence[tuple[str, str]],
        resolve_member_type: Callable[[str], Sequence[tuple[str, str]] | None],
        is_string_like: Callable[[str], bool] | None = None,
    ) -> None:
        from nylium.server.errors import ValidationError

        ast = cls.parse(formula)
        owner = dict(owner_type_props)
        for call in _calls(ast):
            array_key = call.path[0]
            value_type = owner.get(array_key)
            if value_type is None:
                raise ValidationError(
                    f"formula references unknown prop {array_key!r}"
                )
            if not WType.is_array_name(value_type):
                raise ValidationError(
                    f"formula references {array_key!r} which is not an array prop"
                )
            if len(call.path) == 1:
                # bare COUNT(<array>) — no member type to check
                continue
            member_key = call.path[1]
            element_name = WType.element_name(value_type)
            member_props = resolve_member_type(element_name)
            if member_props is None:
                raise ValidationError(
                    f"cannot resolve element type {element_name!r} for {array_key}.{member_key}"
                )
            member_types = dict(member_props)
            member_type = member_types.get(member_key)
            if member_type is None:
                raise ValidationError(
                    f"unknown member prop {array_key}.{member_key}"
                )
            if not _is_numeric(member_type):
                raise ValidationError(
                    f"member prop {array_key}.{member_key} is not numeric ({member_type!r})"
                )
        for ref in _refs(ast):
            value_type = owner.get(ref.key)
            if value_type is None:
                raise ValidationError(
                    f"formula references unknown prop {ref.key!r}"
                )
            if WType.is_array_name(value_type):
                raise ValidationError(
                    f"formula references {ref.key!r} which is an array prop — use SUM({ref.key}.<prop>)"
                )
            if not _is_numeric(value_type):
                raise ValidationError(
                    f"sibling prop {ref.key!r} is not numeric ({value_type!r})"
                )
        for if_node in _ifs(ast):
            value_type = owner.get(if_node.prop)
            if value_type is None:
                raise ValidationError(
                    f"IF condition references unknown prop {if_node.prop!r}"
                )
            if WType.is_array_name(value_type):
                raise ValidationError(
                    f"IF condition prop {if_node.prop!r} is an array — conditions need a scalar"
                )
            string_like = (
                value_type == WString.TYPE_NAME
                if is_string_like is None
                else is_string_like(value_type)
            )
            if string_like:
                if not _is_string_literal(if_node.value):
                    raise ValidationError(
                        f"IF condition prop {if_node.prop!r} is a string/enum — use a quoted literal"
                    )
            else:
                if not _is_numeric(value_type):
                    raise ValidationError(
                        f"IF condition prop {if_node.prop!r} must be String, an enum, or numeric"
                    )
                if _is_string_literal(if_node.value):
                    raise ValidationError(
                        f"IF condition prop {if_node.prop!r} is numeric — use a numeric literal"
                    )

    @classmethod
    def references(cls, formula: str) -> set[tuple[str, str | None]]:
        """Every ``(array key, member key | None)`` pair the formula reads.
        The member is None only for a bare ``COUNT(<array>)``."""
        return {
            (call.path[0], call.path[1] if len(call.path) > 1 else None)
            for call in _calls(cls.parse(formula))
        }

    @classmethod
    def sibling_references(cls, formula: str) -> set[str]:
        """Every sibling prop key the formula reads (ADR-0022), including
        the cond props of IF conditionals (ADR-0024)."""
        ast = cls.parse(formula)
        return {ref.key for ref in _refs(ast)} | {if_node.prop for if_node in _ifs(ast)}

    @classmethod
    def evaluate(
        cls,
        formula: str,
        arrays: Mapping[str, Sequence[Mapping[str, Decimal | Quantity | None]]],
        scalars: Mapping[str, Decimal | Quantity | str | None] | None = None,
    ) -> Decimal | Quantity | None:
        """Fold a formula over live array rows and sibling prop values.
        Unset member/sibling values count as 0 — the ADR-0005 missing-ref
        rule applied to cells; an empty array aggregates to 0. Arithmetic
        promotes to a Quantity when an operand is one (ADR-0022). A
        division by zero (incl. 0/0, which Decimal reports as
        InvalidOperation) yields None — the prop renders empty — rather
        than failing the whole read."""
        try:
            return evaluate_ast(cls.parse(formula), arrays, scalars or {})
        except (ZeroDivisionError, InvalidOperation):
            return None

    @classmethod
    def rewrite(
        cls,
        formula: str,
        array_renames: Mapping[str, str],
        member_renames: Mapping[str, Mapping[str, str]],
    ) -> str:
        """Re-render canonically with prop renames applied. ``member_renames``
        is keyed by the array key as written in the formula (pre-rename)."""
        return render(rewrite_ast(cls.parse(formula), array_renames, member_renames))
