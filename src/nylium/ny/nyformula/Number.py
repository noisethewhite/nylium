from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass


@dataclass(frozen=True)
class Number:
    """A numeric literal."""

    value: Decimal
