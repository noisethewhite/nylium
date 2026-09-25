"""ADR-0005 formula grammar: recursive-descent parser + static validator.

A prop may carry a ``formula`` string that computes its value from the
owner's ``Array<T>`` props, e.g. ``SUM(items.price) * 1.21``. This
package owns the grammar end to end: it parses the string into a small
frozen AST, type-checks that AST against the owner type's schema, folds
the AST over live array rows at read time, and rewrites paths when
props are renamed. One concern per module (ADR-0018):

- ``nodes`` — the frozen AST types + the FUNCTIONS set
- ``parsing`` — tokenizer + recursive-descent parser
- ``formula`` — the Formula class: parse + static schema validation
- ``evaluation`` — read-time folding over live array rows
- ``rewriting`` — canonical rendering + prop-rename rebinding

Grammar (recursive descent, no ``eval``, no third-party deps)::

    expr   := term (('+' | '-') term)*
    term   := factor (('*' | '/') factor)*
    factor := NUMBER | '(' expr ')' | FUNC '(' path ')' | '-' factor
    FUNC   := SUM | AVERAGE | COUNT | MIN | MAX   (case-insensitive)
    path   := IDENT '.' IDENT | IDENT              (bare IDENT only for COUNT)
"""
from nylium.ny.nyformula.evaluation import ArrayRows
from nylium.ny.nyformula.Formula import Formula
from nylium.ny.nyformula.BinOp import BinOp
from nylium.ny.nyformula.Call import Call
from nylium.ny.nyformula.Neg import Neg
from nylium.ny.nyformula.Number import Number
from nylium.ny.nyformula.Ref import Ref
from nylium.ny.nyformula.nodes import Expr
from nylium.Constants import Constants

FUNCTIONS = Constants.Formulas.FUNCTIONS

__all__ = [
    "FUNCTIONS",
    "ArrayRows",
    "BinOp",
    "Call",
    "Expr",
    "Formula",
    "Neg",
    "Number",
    "Ref",
]
