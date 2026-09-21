"""Unit CRUD: create unit types and sync their part drafts (ADR-0015)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from nylium.api.shared import ApiShared
from nylium.database import Database
from nylium.objects.navigation import (
    sync_unit_parts as _sync_unit_parts,
    unit_part_usage,
)
from nylium.tables.objects.unit_parts import unit_parts
from nylium.tables.decor.type_decors import type_decor
from nylium.rows.objects.type import Type
from nylium.objects.wscalar import WColor
from nylium.objects.wtype import WType


class UnitsApi(ApiShared):
    @classmethod
    @Database.commit_after_this
    def create_unit(
        cls,
        name: str,
        base: str,
        secondaries: list[tuple[str, Decimal, Decimal]] | None = None,
        icon: str = "straighten",
        color: str = WColor.DEFAULT,
    ) -> Type:
        """A unit is a type with kind='unit': no props, parts live in
        unit_parts. The base part has identity conversion (multiplier 1,
        offset 0); secondaries are (name, multiplier, offset) with the
        affine convention base = (entered - offset) / multiplier."""
        from nylium.server.errors import ValidationError

        final_name = name.strip()
        if not final_name:
            raise ValidationError("unit name must not be empty")
        base_name = base.strip()
        if not base_name:
            raise ValidationError("unit base name must not be empty")
        cls._check_reserved_name(final_name, "unit name")
        cls._check_color(color)
        cls._check_icon(icon)
        owner = WType.ensure(final_name, kind=WType.KIND_UNIT)
        items: list[tuple[UUID | None, str, Decimal, Decimal, bool]] = [
            (None, base_name, Decimal(1), Decimal(0), True),
            *[(None, n, m, o, False) for n, m, o in (secondaries or [])],
        ]
        cls._validate_unit_draft(items)
        _sync_unit_parts(owner.uuid, final_name, items)
        decor = type_decor[owner.uuid]
        decor.icon = icon
        decor.color = color
        return cls._type_result(final_name)

    @classmethod
    @Database.commit_after_this
    def sync_unit_parts(
        cls, name: str, items: list[tuple[UUID | None, str, Decimal, Decimal, bool]]
    ) -> Type:
        """Apply the unit editor's full part draft at once: matching uuid
        edits in place (a rename propagates to stored values), None
        creates, absent parts are deleted unless still in use. Exactly
        one part is the base; switching the base is refused while any
        value exists — stored magnitudes are canonical, reinterpreting
        them would silently corrupt data."""
        from nylium.server.errors import ValidationError

        owner = WType.by_name(name)
        if owner is None:
            raise KeyError(f"no type {name!r}")
        if not owner.is_unit:
            raise ValidationError(f"type {name!r} is not a unit")
        cls._validate_unit_draft(items)
        old_base = next(
            (p for p in unit_parts.where(type_uuid=owner.uuid) if p.is_base), None
        )
        new_base_uuid = next(uuid for uuid, _, _, _, is_base in items if is_base)
        if (
            old_base is not None
            and new_base_uuid != old_base.uuid
            and unit_part_usage(owner.name) > 0
        ):
            raise ValidationError(
                f"unit {name!r} still has values; its base part cannot change"
            )
        _sync_unit_parts(owner.uuid, owner.name, items)
        return cls._type_result(name)

    @classmethod
    def _validate_unit_draft(
        cls, items: list[tuple[UUID | None, str, Decimal, Decimal, bool]]
    ) -> None:
        from nylium.server.errors import ValidationError

        bases = [name for _, name, _, _, is_base in items if is_base]
        if len(bases) != 1:
            raise ValidationError("a unit needs exactly one base part")
        names = [name for _, name, _, _, _ in items]
        if any(not name.strip() for name in names):
            raise ValidationError("unit part names must not be empty")
        if len(set(names)) != len(names):
            raise ValidationError(f"duplicate unit parts in {names!r}")
        for name, multiplier, offset, is_base in [
            (n, m, o, b) for _, n, m, o, b in items
        ]:
            if multiplier == 0:
                raise ValidationError(f"unit part {name!r} has a zero multiplier")
            if is_base and (multiplier != 1 or offset != 0):
                raise ValidationError(
                    f"the base part {name!r} needs multiplier 1 and offset 0"
                )
