from __future__ import annotations
from nylium.server.bodies.shared import BODY_CONFIG
from uuid import UUID
from pydantic.dataclasses import dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


@dataclass(config=BODY_CONFIG)
class SyncPropItem:
    """One row of the type editor's draft: uuid None = new prop."""

    key: str
    value_type: str
    uuid: UUID | None = None
    # ADR-0005: a formula over the owner's Array<T> props, or None
    formula: str | None = None
    # ADR-0025: a collect member key on the Array<T>'s element type, or None
    collect: str | None = None


resolve_route_hints(sys.modules[__name__])
