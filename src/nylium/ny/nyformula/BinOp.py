# Member of the recursive Expr union: the alias module imports
# this class for the union; the back-reference is TYPE_CHECKING-only.
# pyright: reportImportCycles=false
from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nylium.ny.nyformula.nodes import Expr
from dataclasses import dataclass


@dataclass(frozen=True)
class BinOp:
    """A binary arithmetic node; ``op`` is one of ``+ - * /``."""

    op: str
    left: Expr
    right: Expr
