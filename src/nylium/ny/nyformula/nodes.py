"""ADR-0005 formula AST: the frozen node types a formula parses into.

The closed set of reduction functions lives in ``Constants.Formulas``
so the parser can validate calls without importing the validation layer
back — the package stays a DAG:
nodes → parsing → formula → evaluation/rewriting.
"""
from __future__ import annotations

from typing import NoReturn, TypeAlias
from nylium.server.ValidationError import ValidationError
from nylium.ny.nyformula.BinOp import BinOp
from nylium.ny.nyformula.Call import Call
from nylium.ny.nyformula.If import If
from nylium.ny.nyformula.Neg import Neg
from nylium.ny.nyformula.Number import Number
from nylium.ny.nyformula.Ref import Ref














Expr: TypeAlias = Number | BinOp | Neg | Call | Ref | If



def error(message: str, pos: int) -> NoReturn:
    """Raise a ValidationError with the character offset attached."""

    raise ValidationError(f"{message} at position {pos} in formula")
