from __future__ import annotations
from nylium.objects.nyobject.shared import CONFIG
from nylium.objects.nyobject.ObjectRef import ObjectRef
from pydantic.dataclasses import dataclass


@dataclass(config=CONFIG)
class RefValue:
    """None means the link was never set (or the target is gone)."""

    ref: ObjectRef | None
