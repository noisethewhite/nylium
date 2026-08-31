"""Display DTOs for the whiteout API.

pydantic dataclasses with extra="ignore", the morebuttons convention:
they validate on construction and serialize straight to JSON later,
when FastAPI mounts the Api class.

File-level exception to one-class-per-file: these are peer view types
of the same facade, mirroring the type/object graph they render.
"""
from __future__ import annotations

from uuid import UUID

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from whiteout.objects.wscalar import ScalarPayload

_CONFIG = ConfigDict(extra="ignore")


# --- type schema views ---


@dataclass(config=_CONFIG)
class PropView:
    key: str
    value_type: str


@dataclass(config=_CONFIG)
class TypeView:
    name: str
    props: list[PropView]


# --- object data views ---


@dataclass(config=_CONFIG)
class ObjectRef:
    """A link target rendered for display: who it is, not its whole body."""

    uuid: UUID
    type_name: str


@dataclass(config=_CONFIG)
class ScalarValue:
    """None means the prop was never set."""

    value: ScalarPayload | None


@dataclass(config=_CONFIG)
class RefValue:
    """None means the link was never set (or the target is gone)."""

    ref: ObjectRef | None


@dataclass(config=_CONFIG)
class ArrayValue:
    """None means the prop was never set; [] means set to empty."""

    items: list[PropValue] | None


PropValue = ScalarValue | RefValue | ArrayValue


@dataclass(config=_CONFIG)
class ObjectView:
    """Snapshot of one instance: every prop rendered as a typed
    ScalarValue / RefValue / ArrayValue — no Any escapes."""

    uuid: UUID
    type_name: str
    props: dict[str, PropValue]
