# Member of the recursive Expr union: the alias module imports
# this class for the union; the back-reference is TYPE_CHECKING-only.
# pyright: reportImportCycles=false
from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nylium.objects.nyformula.nodes import Expr
from dataclasses import dataclass


@dataclass(frozen=True)
class If:
    """A conditional (ADR-0024): fold to ``then`` when the owner's ``prop``
    compares true against ``value`` with ``op`` (``==`` or ``!=``), else
    ``else_``. ``value`` keeps the literal exactly as written — quoted for
    a string, bare for a number."""

    prop: str
    op: str
    value: str
    then: Expr
    else_: Expr
