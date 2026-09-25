"""ADR-0005 formula syntax: tokenizer + recursive-descent parser.

Grammar (recursive descent, no ``eval``, no third-party deps)::

    expr   := term (('+' | '-') term)*
    term   := factor (('*' | '/') factor)*
    factor := NUMBER | '(' expr ')' | FUNC '(' path ')' | IDENT | '-' factor
    FUNC   := SUM | AVERAGE | COUNT | MIN | MAX   (case-insensitive)
    path   := IDENT '.' IDENT | IDENT              (bare IDENT only for COUNT)

A bare ``IDENT`` that is not immediately followed by ``'('`` is a
sibling-prop reference (ADR-0022); an ``IDENT`` directly followed by
``'('`` is a function call.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nylium.ny.nyformula.BinOp import BinOp
from nylium.ny.nyformula.Call import Call
from nylium.ny.nyformula.If import If
from nylium.ny.nyformula.Neg import Neg
from nylium.ny.nyformula.Number import Number
from nylium.ny.nyformula.Ref import Ref
from nylium.ny.nyformula.nodes import Expr, error
from nylium.Constants import Constants


@dataclass(frozen=True)
class _Token:
    kind: str
    text: str
    pos: int


def tokenize(formula: str) -> list[_Token]:
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
        if ch == '"' or ch == "'":
            quote = ch
            start = i
            i += 1
            while i < length and formula[i] != quote:
                i += 1
            if i >= length:
                error("unterminated string literal", start)
            i += 1
            tokens.append(_Token("string", formula[start:i], start))
            continue
        if ch == "=":
            if i + 1 < length and formula[i + 1] == "=":
                tokens.append(_Token("eq", "==", i))
                i += 2
                continue
            error(f"unexpected character {ch!r}", i)
        if ch == "!":
            if i + 1 < length and formula[i + 1] == "=":
                tokens.append(_Token("ne", "!=", i))
                i += 2
                continue
            error(f"unexpected character {ch!r}", i)
        if ch == ",":
            tokens.append(_Token("comma", ch, i))
            i += 1
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
            error(f"unexpected character {ch!r}", i)
        i += 1
    tokens.append(_Token("eof", "", length))
    return tokens


class Parser:
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
            error(f"expected {what}", token.pos)
        self._pos += 1
        return token

    def parse(self) -> Expr:
        node = self._expr()
        token = self._peek()
        if token.kind != "eof":
            error(f"unexpected {token.text!r}", token.pos)
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
            name_token = self._advance()
            # an ident directly followed by '(' is a function call (or an
            # IF conditional); a bare ident is a sibling-prop reference
            # (ADR-0022)
            if self._peek().kind == "lparen":
                if name_token.text.upper() == "IF":
                    return self._if()
                return self._call(name_token)
            return Ref(name_token.text)
        error("expected a number, '(', function or '-'", token.pos)

    def _call(self, name_token: _Token) -> Call:
        func = name_token.text.upper()
        if func not in Constants.Formulas.FUNCTIONS:
            error(f"unknown function {name_token.text!r}", name_token.pos)
        _ = self._expect("lparen", "'('")
        first = self._expect("ident", "an array prop key")
        if self._match("dot"):
            member = self._expect("ident", "a member prop key")
            path: tuple[str, ...] = (first.text, member.text)
        else:
            if func != "COUNT":
                error(
                    f"function {func} needs a member path like {first.text}.<prop>",
                    first.pos,
                )
            path = (first.text,)
        _ = self._expect("rparen", "')'")
        return Call(func=func, path=path)

    def _if(self) -> If:
        _ = self._expect("lparen", "'('")
        prop = self._expect("ident", "a prop key")
        op_token = self._peek()
        if op_token.kind not in ("eq", "ne"):
            error("expected '==' or '!='", op_token.pos)
        _ = self._advance()
        value_token = self._peek()
        if value_token.kind not in ("string", "number"):
            error("expected a string or number literal", value_token.pos)
        _ = self._advance()
        _ = self._expect("comma", "','")
        then = self._expr()
        _ = self._expect("comma", "','")
        else_ = self._expr()
        _ = self._expect("rparen", "')'")
        return If(
            prop=prop.text,
            op=op_token.text,
            value=value_token.text,
            then=then,
            else_=else_,
        )
