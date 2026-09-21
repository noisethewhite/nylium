"""String enum CRUD: create enums and sync their option drafts (ADR-0015)."""
from __future__ import annotations

from uuid import UUID

from nylium.api.shared import ApiShared
from nylium.database import Database
from nylium.objects.navigation import sync_enum_options as _sync_enum_options
from nylium.tables.decor import type_decor
from nylium.tables.objects import Type
from nylium.objects.wscalar import WColor
from nylium.objects.wtype import WType


class EnumsApi(ApiShared):
    @classmethod
    @Database.commit_after_this
    def create_enum(
        cls,
        name: str,
        options: list[str] | None = None,
        icon: str = "lists",
        color: str = WColor.DEFAULT,
    ) -> Type:
        """A string enum is a type with kind='enum': no props, values
        live in string_values, options live in enum_options. Options
        here seed the initial list in order."""
        from nylium.server.errors import ValidationError

        final_name = name.strip()
        if not final_name:
            raise ValidationError("enum name must not be empty")
        cls._check_reserved_name(final_name, "enum name")
        cls._check_color(color)
        cls._check_icon(icon)
        owner = WType.ensure(final_name, kind=WType.KIND_ENUM)
        _sync_enum_options(owner.uuid, [(None, v) for v in (options or [])])
        decor = type_decor[owner.uuid]
        decor.icon = icon
        decor.color = color
        return cls._type_result(final_name)

    @classmethod
    @Database.commit_after_this
    def sync_enum_options(
        cls, name: str, items: list[tuple[UUID | None, str]]
    ) -> Type:
        """Apply the enum editor's full option draft at once: matching
        uuid renames the option (propagating to stored values), None
        creates, absent options are deleted unless still in use."""
        from nylium.server.errors import ValidationError

        owner = WType.by_name(name)
        if owner is None:
            raise KeyError(f"no type {name!r}")
        if not owner.is_enum:
            raise ValidationError(f"type {name!r} is not an enum")
        values = [value for _, value in items]
        if any(not value.strip() for value in values):
            raise ValidationError("enum options must not be empty")
        if len(set(values)) != len(values):
            raise ValidationError(f"duplicate enum options in {values!r}")
        _sync_enum_options(owner.uuid, items)
        return cls._type_result(name)
