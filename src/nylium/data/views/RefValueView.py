from __future__ import annotations
from nylium.data.views.ObjectRefView import ObjectRefView
from pydantic.dataclasses import dataclass
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class RefValueView:
    """None means the link was never set (or the target is gone)."""

    ref: ObjectRefView | None
