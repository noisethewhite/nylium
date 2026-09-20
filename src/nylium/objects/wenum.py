# Enum-flavored prop plumbing: an enum-typed prop stores its value in
# string_values like a String, but writes are checked against the
# enum_options of the value type. Shared by WObject attribute access
# and WArray boxing so both enforce the same membership rule.
#
# ADR-0019: all storage statements go through `tables.values.cells`
# (via the objects-layer table alias WString.TABLE) — no Database/sql
# knowledge here.
from __future__ import annotations

from typing import cast
from uuid import UUID

from nylium.database import Database
from nylium.objects.tables.enum_options import enum_options
from nylium.tables.values import cells
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import WString
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
        if value not in [o.value for o in enum_options.where(type_uuid=owner.uuid)]:
            raise ValidationError(f"{value!r} is not an option of enum {type_name}")
        return value

    @classmethod
    @Database.use_same_session
    def read(cls, inst_uuid: UUID, prop: WProp) -> str | None:
        return cast(str | None, cells.read(WString.TABLE, inst_uuid, prop.uuid))

    @classmethod
    @Database.use_same_session
    def write(cls, inst_uuid: UUID, prop: WProp, value: str | None) -> None:
        if value is None:
            _ = cells.clear(WString.TABLE, inst_uuid, prop.uuid)
            return
        cells.write(WString.TABLE, inst_uuid, prop.uuid, value)
