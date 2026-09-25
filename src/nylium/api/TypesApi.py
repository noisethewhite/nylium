"""Type CRUD: create, list, rename and delete user types (ADR-0015)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from nylium.api.ApiShared import ApiShared
from nylium.Constants import Constants

if TYPE_CHECKING:
    # see functions.py: cross-domain calls resolve on the combined Api
    from nylium.api.FunctionsApi import FunctionsApi as _TypesBase
else:
    _TypesBase = ApiShared
from nylium.database import Database
from nylium.data.tables import instances
from nylium.data.tables import props
from nylium.data.tables import type_style
from nylium.data.rows import Type
from nylium.data.tables import types
from nylium.ny.NyProp import NyProp
from nylium.ny.NyColor import NyColor
from nylium.ny.NyScalar import NyScalar
from nylium.ny.NyString import NyString
from nylium.ny.NyType import NyType
from nylium.server.ValidationError import ValidationError
from nylium.uuid import TraitUUID, TypeUUID


class TypesApi(_TypesBase):
    @classmethod
    @Database.use_same_session
    def list_types(cls) -> list[Type]:
        return list(types.all())

    @classmethod
    @Database.use_same_session
    def get_type(cls, name: str) -> Type | None:
        return next(types.where(name=name), None)

    @classmethod
    @Database.commit_after_this
    def create_type(
        cls,
        name: str,
        props: dict[str, str] | None = None,
        plural_name: str | None = None,
        icon: str = "inventory_2",
        color: str = NyColor.DEFAULT,
        embedded: bool = False,
        formulas: dict[str, str] | None = None,
        collects: dict[str, str] | None = None,
    ) -> Type:
        """props maps key -> value type name. Missing value types are created.
        Dict order becomes the schema's display order (positions).
        The schema must open with the `name` prop (String) — see
        Constants.Props.NAME_PROP_KEY. embedded marks a composition type (ADR-0004):
        its instances exist only as a prop value of an owner object.
        formulas maps prop key -> formula string (ADR-0005); a formula
        prop must be Numeric (or Integer for a bare COUNT). collects maps
        prop key -> collect member key (ADR-0025)."""
        # lazy: a module-level import would circle api -> server -> api

        props = dict(props or {})
        formulas = dict(formulas or {})
        collects = dict(collects or {})
        keys = list(props)
        if embedded:
            # ADR-0004 composition types may omit the `name` prop — their
            # instances carry a generated/registry title instead (ADR-0027).
            # When present it must still be a String.
            if Constants.Props.NAME_PROP_KEY in props and props[Constants.Props.NAME_PROP_KEY] != NyString.TYPE_NAME:
                raise ValidationError(
                    f"the {Constants.Props.NAME_PROP_KEY!r} prop must be of type {NyString.TYPE_NAME!r}"
                )
        else:
            if not keys or keys[0] != Constants.Props.NAME_PROP_KEY:
                raise ValidationError(f"first prop of a type must be {Constants.Props.NAME_PROP_KEY!r}")
            if props[Constants.Props.NAME_PROP_KEY] != NyString.TYPE_NAME:
                raise ValidationError(
                    f"the {Constants.Props.NAME_PROP_KEY!r} prop must be of type {NyString.TYPE_NAME!r}"
                )
        cls._check_reserved_name(name, "type name")
        for key in keys:
            # keys land inside generated embedded names — same reservation
            cls._check_reserved_name(key, "prop key")
        strangers = sorted(set(formulas) - set(props))
        if strangers:
            raise ValidationError(
                f"formula keys {strangers!r} do not name a prop of {name!r}"
            )
        collect_strangers = sorted(set(collects) - set(props))
        if collect_strangers:
            raise ValidationError(
                f"collect keys {collect_strangers!r} do not name a prop of {name!r}"
            )
        owner_props = list(props.items())
        for key, value_type_name in props.items():
            formula = formulas.get(key)
            collect = collects.get(key)
            if formula is not None and collect is not None:
                raise ValidationError(
                    f"prop {key!r} cannot be both a formula and a collect prop"
                )
            cls._check_formula_prop(formula, value_type_name, owner_props)
            cls._check_collect_prop(collect, value_type_name, owner_props)
        cls._check_color(color)
        cls._check_icon(icon)
        NyScalar.ensure_builtins()
        owner = NyType.ensure(name, plural_name, embedded=embedded)
        for position, (key, value_type_name) in enumerate(props.items()):
            value_type_uuid, value_trait_uuid = cls._resolve_value_spec(value_type_name)
            _ = NyProp.ensure(
                owner,
                key,
                None if value_type_uuid is None else NyType.by_uuid(TypeUUID.of(value_type_uuid)),
                position,
                formulas.get(key),
                value_trait_uuid=None if value_trait_uuid is None else TraitUUID.of(value_trait_uuid),
                collect=collects.get(key),
            )
        decor = type_style[owner.uuid]
        decor.icon = icon
        decor.color = color
        return cls._type_result(name)

    @classmethod
    @Database.commit_after_this
    def rename_type(
        cls,
        name: str,
        new_name: str | None = None,
        plural_name: str | None = None,
        icon: str | None = None,
        color: str | None = None,
    ) -> Type:
        """Edit a user type's identity: name, plural form, icon, color.
        Builtins and array types (no plural form) are immutable."""  # noqa: E501

        owner = NyType.by_name(name)
        if owner is None:
            raise KeyError(f"no type {name!r}")
        if cls._is_builtin_type(owner):
            raise ValidationError(f"type {name!r} is builtin and cannot be renamed")
        final_name = name if new_name is None else new_name.strip()
        if not final_name:
            raise ValidationError("type name must not be empty")
        cls._check_reserved_name(final_name, "type name")
        collision_row = next(types.where(name=final_name), None)
        if collision_row is not None and collision_row.uuid != owner.uuid:
            raise ValueError(f"type {final_name!r} already exists")
        final_plural = owner.plural_name if plural_name is None else plural_name
        if icon is not None:
            cls._check_icon(icon)
        final_icon = owner.icon if icon is None else icon
        if color is not None:
            cls._check_color(color)
        final_color = owner.color if color is None else color
        row = types[owner.uuid]
        row.name = final_name
        decor = type_style[owner.uuid]
        decor.plural_name = final_plural
        decor.icon = final_icon
        decor.color = final_color
        if owner.is_unit and final_name != name:
            # the parameterized Numeric<Unit> row tags along — prop value
            # types reference it by uuid, only the display name changes
            parameterized_row = next(
                types.where(name=NyType.unit_numeric_name(name)), None
            )
            if parameterized_row is not None:
                parameterized_row.name = NyType.unit_numeric_name(final_name)
                type_style[
                    parameterized_row.uuid
                ].plural_name = f"{NyType.unit_numeric_name(final_name)}s"
        return cls._type_result(final_name)

    @classmethod
    @Database.commit_after_this
    def delete_type(cls, name: str) -> bool:
        """Refuses while instances exist; other types referencing this one
        as a prop value type are stopped by the FK, on purpose."""

        owner = NyType.by_name(name)
        if owner is None:
            return False
        if cls._is_builtin_type(owner):
            raise ValidationError(f"type {name!r} is builtin and cannot be deleted")
        instance_count = sum(1 for _ in instances.where(type_uuid=owner.uuid))
        if instance_count:
            raise ValueError(
                f"type {name!r} still has {instance_count} instances"
            )
        if owner.is_unit:
            # refuse while any prop is parameterized on this unit, then
            # drop the orphaned parameterized row with the unit itself
            parameterized_row = next(
                types.where(name=NyType.unit_numeric_name(name)), None
            )
            if parameterized_row is not None:
                refs = sum(
                    1 for _ in props.where(value_type_uuid=parameterized_row.uuid)
                )
                if refs:
                    raise ValueError(
                        f"unit {name!r} still parameterizes {refs} props"
                    )
                types.delete(parameterized_row.uuid)
        types.delete(owner.uuid)
        return True
