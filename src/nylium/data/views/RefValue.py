from __future__ import annotations
from nylium.data.views.ObjectRef import ObjectRef
from pydantic.dataclasses import dataclass
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class RefValue:
    """None means the link was never set (or the target is gone)."""

    ref: ObjectRef | None
