from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Call:
    """A reduction over an array prop. ``func`` is the uppercase name;
    ``path`` is ``(array_key,)`` for a bare COUNT, else
    ``(array_key, member_key)``."""

    func: str
    path: tuple[str, ...]
