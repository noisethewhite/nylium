"""The derived-tag projection (ADR-0005): one array-membership edge
projected back onto the member object."""
from __future__ import annotations

from uuid import UUID

from pydantic.dataclasses import dataclass

from nylium.objects.wobject.values import CONFIG


@dataclass(config=CONFIG)
class TagView:
    """A derived tag (ADR-0005): one array-membership edge projected back
    onto the member object. Nothing is stored — the name is recomputed on
    every read from the owner's display name and the prop key."""

    owner_uuid: UUID
    owner_name: str
    prop_key: str
    name: str
    # ADR-0005: tag color = the owner type's color, projected along so the
    # UI paints chips without a second fetch
    color: str
