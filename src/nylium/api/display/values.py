"""The PropValue union members (ADR-0011 §5): how one prop crosses the
wire — scalar, link ref, array or inline composition child — plus
ObjectRef, the shared pydantic config and the pinned `name` prop key."""
from __future__ import annotations

from uuid import UUID

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from nylium.objects.wscalar import ScalarPayload

CONFIG = ConfigDict(extra="ignore")

# The object title prop, pinned first on every object type (see
# api.shared.NAME_PROP_KEY). Tags derive the owner's display name from it.
NAME_PROP_KEY = "name"


@dataclass(config=CONFIG)
class ObjectRef:
    """A link target rendered for display: who it is, not its whole body."""

    uuid: UUID
    type_name: str


@dataclass(config=CONFIG)
class ScalarValue:
    """None means the prop was never set. `unit` is the unit part name
    as entered for `Numeric<Unit>` props; absent everywhere else."""

    value: ScalarPayload | None
    unit: str | None = None


@dataclass(config=CONFIG)
class RefValue:
    """None means the link was never set (or the target is gone)."""

    ref: ObjectRef | None


@dataclass(config=CONFIG)
class ArrayValue:
    """None means the prop was never set; [] means set to empty."""

    items: list[PropValue] | None


@dataclass(config=CONFIG)
class EmbeddedValue:
    """A composition child rendered inline (ADR-0004). uuid None means
    the prop was never filled — the child is created lazily on the first
    write. On input, props is the full child draft and uuid is ignored:
    create-vs-update is decided by the existing link, not the client."""

    uuid: UUID | None
    type_name: str
    props: dict[str, PropValue]


PropValue = ScalarValue | RefValue | ArrayValue | EmbeddedValue
