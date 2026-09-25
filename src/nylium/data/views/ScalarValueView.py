from __future__ import annotations
from nylium.ny.NyScalar import ScalarPayload
from pydantic.dataclasses import dataclass
from nylium.Constants import Constants


@dataclass(config=Constants.Pydantic.CONFIG)
class ScalarValueView:
    """None means the prop was never set. `unit` is the unit part name
    as entered for `Numeric<Unit>` props; absent everywhere else."""

    value: ScalarPayload | None
    unit: str | None = None
