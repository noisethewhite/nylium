"""ADR-0005 formula grammar: recursive-descent parser + static validator.

A prop may carry a ``formula`` string that computes its value from the
owner's ``Array<T>`` props, e.g. ``SUM(items.price) * 1.21``. This module
owns the grammar: it parses the string into a small frozen AST, then
type-checks that AST against the owner type's schema. Read-time
evaluation is a later slice and deliberately absent here — nothing in
this module computes a value.

Grammar (recursive descent, no ``eval``, no third-party deps)::

    expr   := term (('+' | '-') term)*
    term   := factor (('*' | '/') factor)*
    factor := NUMBER | '(' expr ')' | FUNC '(' path ')' | '-' factor
    FUNC   := SUM | AVERAGE | COUNT | MIN | MAX   (case-insensitive)
    path   := IDENT '.' IDENT | IDENT              (bare IDENT only for COUNT)
"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar, NoReturn, TypeAlias

from nylium.objects.wscalar import WInteger, WNumeric
from nylium.objects.wtype import WType


# --- AST ---


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
class Call:
    """A reduction over an array prop. ``func`` is the uppercase name;
    ``path`` is ``(array_key,)`` for a bare COUNT, else
    ``(array_key, member_key)``."""

    func: str
    path: tuple[str, ...]


Expr: TypeAlias = Number | BinOp | Neg | Call


def _error(message: str, pos: int) -> NoReturn:
    """Raise a ValidationError with the character offset attached. The
    import is lazy — objects/ importing server/ eagerly would cycle via
    server.app -> routes -> api -> objects."""
    from nylium.server.errors import ValidationError

    raise ValidationError(f"{message} at position {pos} in formula")


# --- tokenizer ---


@dataclass(frozen=True)
class _Token:
    kind: str
    text: str
    pos: int


def _tokenize(formula: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    length = len(formula)
    while i < length:
        ch = formula[i]
        if ch.isspace():
            i += 1
            continue
        if ch.isdigit():
            start = i
            while i < length and formula[i].isdigit():
                i += 1
            if i + 1 < length and formula[i] == "." and formula[i + 1].isdigit():
                i += 1
                while i < length and formula[i].isdigit():
                    i += 1
            tokens.append(_Token("number", formula[start:i], start))
            continue
        if ch.isalpha() or ch == "_":
            start = i
            while i < length and (formula[i].isalnum() or formula[i] == "_"):
                i += 1
            tokens.append(_Token("ident", formula[start:i], start))
            continue
        if ch == "(":
            tokens.append(_Token("lparen", ch, i))
        elif ch == ")":
            tokens.append(_Token("rparen", ch, i))
        elif ch == "+":
            tokens.append(_Token("plus", ch, i))
        elif ch == "-":
            tokens.append(_Token("minus", ch, i))
        elif ch == "*":
            tokens.append(_Token("star", ch, i))
        elif ch == "/":
            tokens.append(_Token("slash", ch, i))
        elif ch == ".":
            tokens.append(_Token("dot", ch, i))
        else:
            _error(f"unexpected character {ch!r}", i)
        i += 1
    tokens.append(_Token("eof", "", length))
    return tokens


# --- recursive-descent parser ---


class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self._tokens: list[_Token] = tokens
        self._pos: int = 0

    def _peek(self) -> _Token:
        return self._tokens[self._pos]

    def _advance(self) -> _Token:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _match(self, kind: str) -> bool:
        if self._peek().kind == kind:
            self._pos += 1
            return True
        return False

    def _expect(self, kind: str, what: str) -> _Token:
        token = self._peek()
        if token.kind != kind:
            _error(f"expected {what}", token.pos)
        self._pos += 1
        return token

    def parse(self) -> Expr:
        node = self._expr()
        token = self._peek()
        if token.kind != "eof":
            _error(f"unexpected {token.text!r}", token.pos)
        return node

    def _expr(self) -> Expr:
        node = self._term()
        while self._peek().kind in ("plus", "minus"):
            op = self._advance().text
            right = self._term()
            node = BinOp(op=op, left=node, right=right)
        return node

    def _term(self) -> Expr:
        node = self._factor()
        while self._peek().kind in ("star", "slash"):
            op = self._advance().text
            right = self._factor()
            node = BinOp(op=op, left=node, right=right)
        return node

    def _factor(self) -> Expr:
        token = self._peek()
        if token.kind == "number":
            _ = self._advance()
            return Number(Decimal(token.text))
        if token.kind == "minus":
            _ = self._advance()
            return Neg(self._factor())
        if token.kind == "lparen":
            _ = self._advance()
            node = self._expr()
            _ = self._expect("rparen", "')'")
            return node
        if token.kind == "ident":
            return self._call()
        _error("expected a number, '(', function or '-'", token.pos)

    def _call(self) -> Call:
        name_token = self._advance()
        func = name_token.text.upper()
        if func not in Formula.FUNCTIONS:
            _error(f"unknown function {name_token.text!r}", name_token.pos)
        _ = self._expect("lparen", "'('")
        first = self._expect("ident", "an array prop key")
        if self._match("dot"):
            member = self._expect("ident", "a member prop key")
            path: tuple[str, ...] = (first.text, member.text)
        else:
            if func != "COUNT":
                _error(
                    f"function {func} needs a member path like {first.text}.<prop>",
                    first.pos,
                )
            path = (first.text,)
        _ = self._expect("rparen", "')'")
        return Call(func=func, path=path)


def _calls(node: Expr) -> Iterator[Call]:
    """Every Call node in the AST, depth-first."""
    if isinstance(node, Call):
        yield node
    elif isinstance(node, BinOp):
        yield from _calls(node.left)
        yield from _calls(node.right)
    elif isinstance(node, Neg):
        yield from _calls(node.operand)


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

    FUNCTIONS: ClassVar[frozenset[str]] = frozenset(
        {"SUM", "AVERAGE", "COUNT", "MIN", "MAX"}
    )

    @classmethod
    def parse(cls, formula: str) -> Expr:
        return _Parser(_tokenize(formula)).parse()

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
