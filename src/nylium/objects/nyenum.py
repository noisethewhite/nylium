# Enum-flavored prop plumbing: an enum-typed prop stores its value in
# string_values like a String, but writes are checked against the
# enum_options of the value type. Shared by NyObject attribute access
# and NyArray boxing so both enforce the same membership rule.
#
# ADR-0019: all storage statements go through `StringValues`
# (the string_values store) — no Database/sql knowledge here.
from __future__ import annotations

from typing import Self, cast
from uuid import UUID

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from nylium.data.tables import StringValues

from nylium.database import Database
from nylium.data.rows import EnumOption
from nylium.data.tables import enum_options
from nylium.objects.nyprop import NyProp
from nylium.objects.NyType import NyType
from nylium.server.errors import ValidationError


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
    def read(cls, inst_uuid: UUID, prop: NyProp) -> str | None:
        return cast(str | None, StringValues.read(inst_uuid, prop.uuid))

    @classmethod
    @Database.use_same_session
    def write(cls, inst_uuid: UUID, prop: NyProp, value: str | None) -> None:
        if value is None:
            _ = StringValues.clear(inst_uuid, prop.uuid)
            return
        StringValues.write(inst_uuid, prop.uuid, value)


_VIEW_CONFIG = ConfigDict(strict=True)


@dataclass(config=_VIEW_CONFIG)
class EnumOptionView:
    """One enum option (contracts.ts EnumOptionView) — the wire
    projection, kept next to the domain facade it renders."""

    uuid: UUID
    value: str

    @classmethod
    def from_row(cls, option: EnumOption) -> Self:
        return cls(uuid=option.uuid, value=option.value)
