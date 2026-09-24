# Member of the recursive PropValue union: the alias module imports
# this class for the union; the back-reference is TYPE_CHECKING-only.
# pyright: reportImportCycles=false
from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nylium.objects.nyobject.values import PropValue
from nylium.objects.nyobject.shared import CONFIG
from pydantic.dataclasses import dataclass


@dataclass(config=CONFIG)
class ArrayValue:
    """None means the prop was never set; [] means set to empty."""

    items: list[PropValue] | None
