from __future__ import annotations
from nylium.objects.nyobject.shared import CONFIG
from nylium.objects.nyscalar import ScalarPayload
from pydantic.dataclasses import dataclass


@dataclass(config=CONFIG)
class ScalarValue:
    """None means the prop was never set. `unit` is the unit part name
    as entered for `Numeric<Unit>` props; absent everywhere else."""

    value: ScalarPayload | None
    unit: str | None = None
