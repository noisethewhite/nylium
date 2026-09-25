"""TypedObjectUUID — base for ObjectUUID subclasses that verify the
instance's type name on construction."""
from __future__ import annotations

from typing import ClassVar, Self, override
from uuid import UUID

from nylium.data.tables import instances, types
from nylium.uuid.ObjectUUID import ObjectUUID


class TypedObjectUUID(ObjectUUID):
    """An instance uuid that only accepts instances of one built-in type."""

    TYPE_NAME: ClassVar[str]

    @classmethod
    @override
    def of(cls, value: UUID) -> Self:
        inst = instances.get(value)
        if inst is None:
            raise KeyError(f"no instance {value}")
        t = types.get(inst.type_uuid)
        if t is None or t.name != cls.TYPE_NAME:
            raise TypeError(f"{value} is not a {cls.TYPE_NAME} instance")
        return cls(str(value))
