# Member of the recursive PropValue union: the alias module imports
# this class for the union; the back-reference is TYPE_CHECKING-only.
# pyright: reportImportCycles=false
from __future__ import annotations

from typing import TYPE_CHECKING
from nylium.Constants import Constants


if TYPE_CHECKING:
    from nylium.data.views.values import PropValue
from uuid import UUID
from pydantic.dataclasses import dataclass


@dataclass(config=Constants.Pydantic.CONFIG)
class EmbeddedValue:
    """A composition child rendered inline (ADR-0004). uuid None means
    the prop was never filled — the child is created lazily on the first
    write. On input, props is the full child draft and uuid is ignored:
    create-vs-update is decided by the existing link, not the client."""

    uuid: UUID | None
    type_name: str
    props: dict[str, PropValue]
