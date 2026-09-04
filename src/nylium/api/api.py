"""Api: classmethod facade over the object layer — CRUD on types and
objects, returning the dataclass views from views.py.

This is the seam a future HTTP app (FastAPI) mounts. It never leaks
WObject wrappers or SQLAlchemy rows to callers: everything in and out
is a view, a UUID, or a plain python value. Writes go through the
WObject layer, so all type validation applies here too.

Table access lives on the table classes themselves (Types/Instances/
Props helpers); this file only orchestrates and adapts caller input.
"""
from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import TypeAlias, cast
from uuid import UUID

from nylium.api.views import ObjectRef, ObjectView, TypeView
from nylium.database import Database, EnumOptions, Instances, Props, Types, UnitParts
from nylium.objects.wenum import WEnum
from nylium.objects.wobject import WObject
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import WScalar, WString
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue, WTypeMeta

# What callers may hand in for a prop: stored values, plus links as
# UUID/ObjectRef (resolved to WObject here). A string forward ref inside
# list[...] keeps the recursion 3.11-parseable without typing.Union.
PropInput: TypeAlias = StoredValue | UUID | ObjectRef | list["PropInput"]

# Every object type starts with a `name` prop — it IS the instance's
# title, rendered as the editable heading in the UI. Pinned at
# position 0: reorder may shuffle the rest, never the name.
NAME_PROP_KEY = "name"


class Api:
    # --- types ---

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def list_types(cls) -> list[TypeView]:
        return [TypeView.from_name(name) for name in Types.all_names()]

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def get_type(cls, name: str) -> TypeView | None:
        if WType.by_name(name) is None:
            return None
        return TypeView.from_name(name)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def create_type(
        cls,
        name: str,
        props: dict[str, str] | None = None,
        plural_name: str | None = None,
        icon: str = "inventory_2",
        color: str = "gray",
    ) -> TypeView:
        """props maps key -> value type name. Missing value types are created.
        Dict order becomes the schema's display order (positions).
        The schema must open with the `name` prop (String) — see
        NAME_PROP_KEY."""
        # lazy: a module-level import would circle api -> server -> api
        from nylium.server.errors import ValidationError

        props = dict(props or {})
        keys = list(props)
        if not keys or keys[0] != NAME_PROP_KEY:
            raise ValidationError(f"first prop of a type must be {NAME_PROP_KEY!r}")
        if props[NAME_PROP_KEY] != WString.TYPE_NAME:
            raise ValidationError(
                f"the {NAME_PROP_KEY!r} prop must be of type {WString.TYPE_NAME!r}"
            )
        WScalar.ensure_builtins()
        owner = WType.ensure(name, plural_name)
        for position, (key, value_type_name) in enumerate(props.items()):
            _ = WProp.ensure(owner, key, cls._ensure_value_type(value_type_name), position)
        Types.update(owner.uuid, owner.name, owner.plural_name, icon, color)
        return TypeView.from_name(name)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def create_enum(
        cls,
        name: str,
        options: list[str] | None = None,
        icon: str = "lists",
        color: str = "gray",
    ) -> TypeView:
        """A string enum is a type with kind='enum': no props, values
        live in string_values, options live in enum_options. Options
        here seed the initial list in order."""
        from nylium.server.errors import ValidationError

        final_name = name.strip()
        if not final_name:
            raise ValidationError("enum name must not be empty")
        owner = WType.ensure(final_name, kind=WType.KIND_ENUM)
        EnumOptions.sync(owner.uuid, [(None, v) for v in (options or [])])
        Types.update(owner.uuid, owner.name, None, icon, color)
        return TypeView.from_name(final_name)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def sync_enum_options(
        cls, name: str, items: list[tuple[UUID | None, str]]
    ) -> TypeView:
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
        EnumOptions.sync(owner.uuid, items)
        return TypeView.from_name(name)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def create_unit(
        cls,
        name: str,
        base: str,
        secondaries: list[tuple[str, Decimal, Decimal]] | None = None,
        icon: str = "straighten",
        color: str = "gray",
    ) -> TypeView:
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
        owner = WType.ensure(final_name, kind=WType.KIND_UNIT)
        items: list[tuple[UUID | None, str, Decimal, Decimal, bool]] = [
            (None, base_name, Decimal(1), Decimal(0), True),
            *[(None, n, m, o, False) for n, m, o in (secondaries or [])],
        ]
        cls._validate_unit_draft(items)
        UnitParts.sync(owner.uuid, final_name, items)
        Types.update(owner.uuid, owner.name, None, icon, color)
        return TypeView.from_name(final_name)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def sync_unit_parts(
        cls, name: str, items: list[tuple[UUID | None, str, Decimal, Decimal, bool]]
    ) -> TypeView:
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
        old_base = UnitParts.base_of(owner.uuid)
        new_base_uuid = next(uuid for uuid, _, _, _, is_base in items if is_base)
        if (
            old_base is not None
            and new_base_uuid != old_base.uuid
            and UnitParts.usage_total(owner.name) > 0
        ):
            raise ValidationError(
                f"unit {name!r} still has values; its base part cannot change"
            )
        UnitParts.sync(owner.uuid, owner.name, items)
        return TypeView.from_name(name)

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

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def reorder_props(cls, type_name: str, keys: list[str]) -> TypeView:
        """Persist a new prop order; keys must cover the whole schema and
        keep the `name` prop first (see NAME_PROP_KEY)."""
        from nylium.server.errors import ValidationError

        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        existing = [prop.key for prop in WProp.all_for(owner)]
        if set(keys) != set(existing):
            raise ValueError(f"prop order {keys!r} does not match {type_name!r} schema")
        if NAME_PROP_KEY in existing and (not keys or keys[0] != NAME_PROP_KEY):
            raise ValidationError(f"the {NAME_PROP_KEY!r} prop must stay first")
        WProp.reorder(owner, keys)
        return TypeView.from_name(type_name)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def sync_props(
        cls, type_name: str, items: list[tuple[UUID | None, str, str]]
    ) -> TypeView:
        """Apply the type editor's full prop draft at once. Each item is
        (uuid | None, key, value type name): a matching uuid edits that
        prop in place (rename/retype — a retype purges the old values),
        None creates a new prop, props absent from the draft are deleted
        for every instance at once. The pinned `name` prop must keep its
        uuid, its key, its String type and the first position."""
        from nylium.server.errors import ValidationError

        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        existing = WProp.all_for(owner)
        by_uuid = {prop.uuid: prop for prop in existing}
        name_prop = next(
            (prop for prop in existing if prop.key == NAME_PROP_KEY), None
        )
        if not items:
            raise ValidationError("a type must keep at least its 'name' prop")
        first_uuid, first_key, first_type = items[0]
        if (
            name_prop is not None
            and (first_uuid, first_key, first_type)
            != (name_prop.uuid, NAME_PROP_KEY, WString.TYPE_NAME)
        ):
            raise ValidationError(
                f"the {NAME_PROP_KEY!r} prop must stay first, keyed {NAME_PROP_KEY!r}, typed {WString.TYPE_NAME!r}"
            )
        keys = [key for _, key, _ in items]
        if any(not key.strip() for key in keys):
            raise ValidationError("prop keys must not be empty")
        if len(set(keys)) != len(keys):
            raise ValidationError(f"duplicate prop keys in {keys!r}")
        strangers = [uuid for uuid, _, _ in items if uuid is not None and uuid not in by_uuid]
        if strangers:
            raise ValidationError(f"prop uuids {strangers!r} do not belong to {type_name!r}")
        resolved: list[tuple[UUID | None, str, UUID]] = [
            (uuid, key, cls._ensure_value_type(value_type_name).uuid)
            for uuid, key, value_type_name in items
        ]
        WProp.sync_schema(owner, resolved)
        return TypeView.from_name(type_name)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def rename_type(
        cls,
        name: str,
        new_name: str | None = None,
        plural_name: str | None = None,
        icon: str | None = None,
        color: str | None = None,
    ) -> TypeView:
        """Edit a user type's identity: name, plural form, icon, color.
        Builtins and array types (no plural form) are immutable."""  # noqa: E501
        from nylium.server.errors import ValidationError

        owner = WType.by_name(name)
        if owner is None:
            raise KeyError(f"no type {name!r}")
        if owner.plural_name is None and not owner.is_enum and not owner.is_unit:
            raise ValidationError(f"type {name!r} is builtin and cannot be renamed")
        final_name = name if new_name is None else new_name.strip()
        if not final_name:
            raise ValidationError("type name must not be empty")
        collision = Types.uuid_by_name(final_name)
        if collision is not None and collision != owner.uuid:
            raise ValueError(f"type {final_name!r} already exists")
        final_plural = owner.plural_name if plural_name is None else plural_name
        final_icon = owner.icon if icon is None else icon
        final_color = owner.color if color is None else color
        Types.update(owner.uuid, final_name, final_plural, final_icon, final_color)
        if owner.is_unit and final_name != name:
            # the parameterized Numeric<Unit> row tags along — prop value
            # types reference it by uuid, only the display name changes
            parameterized_uuid = Types.uuid_by_name(WType.unit_numeric_name(name))
            if parameterized_uuid is not None:
                parameterized = WType.by_uuid(parameterized_uuid)
                if parameterized is not None:
                    Types.update(
                        parameterized_uuid,
                        WType.unit_numeric_name(final_name),
                        None,
                        parameterized.icon,
                        parameterized.color,
                    )
        return TypeView.from_name(final_name)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def delete_type(cls, name: str) -> bool:
        """Refuses while instances exist; other types referencing this one
        as a prop value type are stopped by the FK, on purpose."""
        owner = WType.by_name(name)
        if owner is None:
            return False
        instance_count = Instances.count_of_type(owner.uuid)
        if instance_count:
            raise ValueError(
                f"type {name!r} still has {instance_count} instances"
            )
        if owner.is_unit:
            # refuse while any prop is parameterized on this unit, then
            # drop the orphaned parameterized row with the unit itself
            parameterized_uuid = Types.uuid_by_name(WType.unit_numeric_name(name))
            if parameterized_uuid is not None:
                refs = Props.count_with_value_type(parameterized_uuid)
                if refs:
                    raise ValueError(
                        f"unit {name!r} still parameterizes {refs} props"
                    )
                Types.delete_by_uuid(parameterized_uuid)
        Types.delete_by_uuid(owner.uuid)
        return True

    # --- objects ---

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def list_objects(cls, type_name: str) -> list[ObjectView]:
        owner = WType.by_name(type_name)
        if owner is None:
            return []
        views = [
            ObjectView.from_uuid(uuid)
            for uuid in Instances.uuids_of_type(owner.uuid)
        ]
        return [view for view in views if view is not None]

    @classmethod
    def get_object(cls, uuid: UUID) -> ObjectView | None:
        return ObjectView.from_uuid(uuid)

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def create_object(
        cls, type_name: str, props: dict[str, PropInput] | None = None
    ) -> ObjectView:
        normalized = cls._normalize_props(type_name, props or {})
        klass = WTypeMeta.python_class(type_name)
        if klass is not None:
            # **props forwarding: the dict can't collide with _uuid in
            # practice (prop keys), but the checker can't prove it
            ctor = cast(Callable[..., WObject], klass)
            instance_uuid = ctor(**normalized).uuid
        else:
            instance_uuid = WObject.create_db_only(type_name, normalized)
        view = cls.get_object(instance_uuid)
        if view is None:
            raise RuntimeError(f"created {type_name} instance {instance_uuid} vanished")
        return view

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def update_object(cls, uuid: UUID, props: dict[str, PropInput]) -> ObjectView:
        wrapper = WObject.wrap(uuid)
        type_name = Instances.get_type_name(uuid)
        normalized = cls._normalize_props(type_name, props)
        for key, value in normalized.items():
            setattr(wrapper, key, value)
        view = cls.get_object(uuid)
        if view is None:
            raise RuntimeError(f"updated instance {uuid} vanished")
        return view

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def delete_object(cls, uuid: UUID) -> bool:
        if not Instances.exists(uuid):
            return False
        WObject.wrap(uuid).delete()
        return True

    # --- internals ---

    @classmethod
    def _ensure_value_type(cls, name: str) -> WType:
        """Resolve a prop value type name for create_type/sync_props.
        Beyond WType.ensure this validates the parameterized forms:
        `Numeric<Unit>` needs an existing unit type, and a bare unit type
        name is meaningless as a prop type — the parameter is mandatory."""
        from nylium.server.errors import ValidationError

        unit_param = WType.unit_param_of(name)
        if unit_param is not None:
            unit = WType.by_name(unit_param)
            if unit is None or not unit.is_unit:
                raise ValidationError(f"no unit type {unit_param!r}")
            return WType.ensure(name)
        if WType.is_array_name(name):
            _ = cls._ensure_value_type(WType.element_name(name))
            return WType.ensure(name)
        resolved = WType.ensure(name)
        if resolved.is_unit:
            raise ValidationError(
                f"unit type {name!r} needs a numeric parameter: {WType.unit_numeric_name(name)}"
            )
        return resolved

    @classmethod
    @Database.sessionmethod(bundled=True, commit=False)
    def _normalize_props(
        cls, type_name: str, props: dict[str, PropInput]
    ) -> dict[str, StoredValue]:
        """Callers hand links over as UUID/ObjectRef (that's all they have);
        the object layer wants WObject wrappers. Resolve by prop type."""
        owner_type_uuid = Types.uuid_by_name(type_name)
        if owner_type_uuid is None:
            raise KeyError(f"no type {type_name!r}")
        return {
            key: cls._normalize_value(value, Props.get_type_name(owner_type_uuid, key))
            for key, value in props.items()
        }

    @classmethod
    def _normalize_value(cls, value: PropInput, type_name: str) -> StoredValue:
        if WScalar.by_type_name(type_name) is not None:
            return cast(StoredValue, value)
        if WType.unit_param_of(type_name) is not None:
            return cast(StoredValue, value)  # Quantity; parts checked in setattr
        if WEnum.is_enum(type_name):
            return cast(StoredValue, value)  # membership checked in setattr
        if WType.is_array_name(type_name):
            if not isinstance(value, list):
                raise TypeError(f"array prop takes list, got {type(value).__name__}")
            element_name = WType.element_name(type_name)
            return [cls._normalize_value(item, element_name) for item in value]
        if isinstance(value, ObjectRef):
            return WObject.wrap(value.uuid)
        if isinstance(value, UUID):
            return WObject.wrap(value)
        return cast(StoredValue, value)  # anything else fails in setattr
