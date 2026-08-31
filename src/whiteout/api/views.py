"""Display DTOs for the whiteout API.

pydantic dataclasses with extra="ignore", the morebuttons convention:
they validate on construction and serialize straight to JSON later,
when FastAPI mounts the Api class.

File-level exception to one-class-per-file: these are peer view types
of the same facade, mirroring the type/object graph they render.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

_CONFIG = ConfigDict(extra="ignore")


@dataclass(config=_CONFIG)
class PropView:
    key: str
    value_type: str


@dataclass(config=_CONFIG)
class TypeView:
    name: str
    props: list[PropView]


@dataclass(config=_CONFIG)
class ObjectRef:
    """A link target rendered for display: who it is, not its whole body."""

    uuid: UUID
    type_name: str


@dataclass(config=_CONFIG)
class ObjectView:
    """Snapshot of one instance. Scalars as-is, links as ObjectRef,
    arrays as lists of either."""

    uuid: UUID
    type_name: str
    props: dict[str, Any]
