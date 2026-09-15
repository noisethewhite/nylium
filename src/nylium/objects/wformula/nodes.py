"""ADR-0005 formula AST: the frozen node types a formula parses into.

``FUNCTIONS`` is the closed set of reduction functions; it lives here
(not on ``Formula``) so the parser can validate calls without importing
the validation layer back — the package stays a DAG:
nodes → parsing → formula → evaluation/rewriting.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import NoReturn, TypeAlias


@dataclass(frozen=True)
class Number:
    """A numeric literal."""

    value: Decimal


@dataclass(frozen=True)
class BinOp:
    """A binary arithmetic node; ``op`` is one of ``+ - * /``."""

    op: str
    left: Expr
    right: Expr


@dataclass(frozen=True)
class Neg:
    """Unary minus."""

    operand: Expr


@dataclass(frozen=True)
class Ref:
    """A sibling-prop reference (ADR-0022): a bare identifier naming
    another prop of the same owner. Evaluates to the sibling's stored
    scalar value (0 when unset)."""

    key: str


@dataclass(frozen=True)
class Call:
    """A reduction over an array prop. ``func`` is the uppercase name;
    ``path`` is ``(array_key,)`` for a bare COUNT, else
    ``(array_key, member_key)``."""

    func: str
    path: tuple[str, ...]


Expr: TypeAlias = Number | BinOp | Neg | Call | Ref

FUNCTIONS: frozenset[str] = frozenset({"SUM", "AVERAGE", "COUNT", "MIN", "MAX"})


def error(message: str, pos: int) -> NoReturn:
    """Raise a ValidationError with the character offset attached. The
    import is lazy — objects/ importing server/ eagerly would cycle via
    server.app -> routes -> api -> objects."""
    from nylium.server.errors import ValidationError

    raise ValidationError(f"{message} at position {pos} in formula")
