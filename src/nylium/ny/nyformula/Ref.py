from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Ref:
    """A sibling-prop reference (ADR-0022): a bare identifier naming
    another prop of the same owner. Evaluates to the sibling's stored
    scalar value (0 when unset)."""

    key: str
