"""ArrayUUID — an ObjectUUID that only accepts ``Array<...>`` instances."""
from __future__ import annotations

from typing import Self, override
from uuid import UUID

from nylium.data.tables import instances, types
from nylium.uuid.ObjectUUID import ObjectUUID


class ArrayUUID(ObjectUUID):
    """An instance uuid whose instance is an ``Array<...>``."""

    @classmethod
    @override
    def of(cls, value: UUID) -> Self:
        inst = instances.get(value)
        if inst is None:
            raise KeyError(f"no instance {value}")
        t = types.get(inst.type_uuid)
        if t is None or not t.name.startswith("Array<"):
            raise TypeError(f"{value} is not an Array<...> instance")
        return cls(str(value))
