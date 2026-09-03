# Enum-flavored prop plumbing: an enum-typed prop stores its value in
# string_values like a String, but writes are checked against the
# enum_options of the value type. Shared by WObject attribute access
# and WArray boxing so both enforce the same membership rule.
from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy.orm import Session

from nylium.database.tables import EnumOptions, StringValues
from nylium.objects.wprop import WProp
from nylium.objects.wtype import WType
from nylium.server.errors import ValidationError


class WEnum:
    @classmethod
    def is_enum(cls, type_name: str) -> bool:
        owner = WType.by_name(type_name)
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
        owner = WType.by_name(type_name)
        if owner is None or not owner.is_enum:
            raise KeyError(f"no enum {type_name!r}")
        if value not in EnumOptions.values_of(owner.uuid):
            raise ValidationError(f"{value!r} is not an option of enum {type_name}")
        return value

    @classmethod
    def read(cls, session: Session, inst_uuid: UUID, prop: WProp) -> str | None:
        row = session.get(StringValues, (inst_uuid, prop.uuid))
        return None if row is None else cast(str | None, row.value)

    @classmethod
    def write(cls, session: Session, inst_uuid: UUID, prop: WProp, value: str | None) -> None:
        row = session.get(StringValues, (inst_uuid, prop.uuid))
        if value is None:
            if row is not None:
                session.delete(row)
            return
        if row is None:
            session.add(StringValues(inst_uuid=inst_uuid, prop_uuid=prop.uuid, value=value))
            return
        row.value = value
