from __future__ import annotations
from nylium.database import Database
from nylium.objects.NyProp import NyProp
from nylium.objects.NyType import NyType
from nylium.data.tables import StringValues
from nylium.uuid import ObjectUUID
from nylium.server.ValidationError import ValidationError
from typing import cast
from nylium.data.tables import enum_options


class NyEnum:
    @classmethod
    def is_enum(cls, type_name: str) -> bool:
        owner = NyType.by_name(type_name)
        return owner is not None and owner.is_enum

    @classmethod
    def validate(cls, type_name: str, value: object) -> str | None:
        """None unsets; anything else must be a str from the option list."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError(
                f"enum {type_name} takes str, got {type(value).__name__}"
            )
        owner = NyType.by_name(type_name)
        if owner is None or not owner.is_enum:
            raise KeyError(f"no enum {type_name!r}")
        if value not in [o.value for o in enum_options.where(type_uuid=owner.uuid)]:
            raise ValidationError(f"{value!r} is not an option of enum {type_name}")
        return value

    @classmethod
    @Database.use_same_session
    def read(cls, inst_uuid: ObjectUUID, prop: NyProp) -> str | None:
        return cast(str | None, StringValues.read(inst_uuid, prop.uuid))

    @classmethod
    @Database.use_same_session
    def write(cls, inst_uuid: ObjectUUID, prop: NyProp, value: str | None) -> None:
        if value is None:
            _ = StringValues.clear(inst_uuid, prop.uuid)
            return
        StringValues.write(inst_uuid, prop.uuid, value)
