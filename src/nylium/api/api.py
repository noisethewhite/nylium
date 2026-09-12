"""Api: classmethod facade over the object layer — CRUD on types and
objects, returning table-domain objects (ADR-0011) and the aggregate
views from views.py.

This is the seam a future HTTP app (FastAPI) mounts. It never leaks
WObject wrappers or SQLAlchemy rows to callers: everything in and out
is a domain object, a UUID, or a plain python value. Writes go through
the WObject layer, so all type validation applies here too.

Table access lives on the table classes themselves (Types/TABLE_Instances/
TABLE_Props helpers); this file only orchestrates and adapts caller input.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import TypeAlias, cast
from uuid import UUID, uuid4

from nylium.api.views import FunctionView, ObjectRef, ObjectView
from nylium.database import databasemethod
from nylium.tables.files import File
from nylium.tables.objects.types import Type, types
from nylium.tables import (
    Trait,
    enum_options,
    files,
    instances,
    props,
    traits,
    type_traits,
    unit_parts,
)
from nylium.objects.wembedded import EMBEDDED_NAME_SEPARATOR, WEmbedded
from nylium.objects.wenum import WEnum
from nylium.objects.wfile import WFile
from nylium.objects.wformula import Formula
from nylium.objects.wfunction import INPUT_PROP_KEY, WFunction
from nylium.objects.wobject import WObject
from nylium.objects.wprop import SchemaItem, WProp
from nylium.objects.wscalar import WColor, WInteger, WNumeric, WScalar, WString
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue, WTypeMeta


def _prop_value_type_name(owner_type_uuid: UUID, key: str) -> str:
    """The value-spec name of one effective prop — what `_normalize_value`
    needs. ADR-0013: the effective schema includes attached traits' props."""
    owner = types.get(owner_type_uuid)
    if owner is None:
        raise KeyError(f"type <gone> has no prop {key!r}")
    prop = next((p for p in owner.props if p.key == key), None)
    if prop is None:
        raise KeyError(f"type {owner.name!r} has no prop {key!r}")
    return prop.value_type


def _is_builtin_type(owner: WType) -> bool:
    """Immutable system type: scalars, array forms, parameterized kinds
    (Numeric<Unit>, Function<T,R>) and the file kinds. Mirrors the
    frontend's `isUserType` — a user type is mutable even without a plural
    name. Lives here, not on WType, because it needs WScalar (which imports
    WType — keeping the object layer acyclic)."""
    name = owner.name
    return (
        owner.is_file
        or WScalar.is_scalar(name)
        or WType.is_array_name(name)
        or WType.unit_param_of(name) is not None
        or WType.is_function_name(name)
    )


# What callers may hand in for a prop: stored values, plus links as
# UUID/ObjectRef (resolved to WObject here), plus a props draft for
# embedded (composition) props — ADR-0004. A string forward ref inside
# list[...] keeps the recursion 3.11-parseable without typing.Union.
PropInput: TypeAlias = (
    StoredValue | UUID | ObjectRef | list["PropInput"] | dict[str, "PropInput"]
)

# Every object type starts with a `name` prop — it IS the instance's
# title, rendered as the editable heading in the UI. Pinned at
# position 0: reorder may shuffle the rest, never the name.
NAME_PROP_KEY = "name"


class Api:
    # --- types ---

    @classmethod
    @databasemethod(commit=False)
    def list_types(cls) -> list[Type]:
        return list(types.all())

    @classmethod
    @databasemethod(commit=False)
    def get_type(cls, name: str) -> Type | None:
        return next(types.where(name=name), None)

    @classmethod
    def _type_result(cls, name: str) -> Type:
        """Re-read a type the caller just wrote, for the return value.
        The write path resolves the name first, so a miss means a bug."""
        result = next(types.where(name=name), None)
        if result is None:
            raise RuntimeError(f"type {name!r} vanished after write")
        return result

    @classmethod
    @databasemethod(commit=True)
    def create_type(
        cls,
        name: str,
        props: dict[str, str] | None = None,
        plural_name: str | None = None,
        icon: str = "inventory_2",
        color: str = WColor.DEFAULT,
        embedded: bool = False,
        formulas: dict[str, str] | None = None,
    ) -> Type:
        """props maps key -> value type name. Missing value types are created.
        Dict order becomes the schema's display order (positions).
        The schema must open with the `name` prop (String) — see
        NAME_PROP_KEY. embedded marks a composition type (ADR-0004):
        its instances exist only as a prop value of an owner object.
        formulas maps prop key -> formula string (ADR-0005); a formula
        prop must be Numeric (or Integer for a bare COUNT)."""
        # lazy: a module-level import would circle api -> server -> api
        from nylium.server.errors import ValidationError

        props = dict(props or {})
        formulas = dict(formulas or {})
        keys = list(props)
        if not keys or keys[0] != NAME_PROP_KEY:
            raise ValidationError(f"first prop of a type must be {NAME_PROP_KEY!r}")
        if props[NAME_PROP_KEY] != WString.TYPE_NAME:
            raise ValidationError(
                f"the {NAME_PROP_KEY!r} prop must be of type {WString.TYPE_NAME!r}"
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
        owner_props = list(props.items())
        for key, value_type_name in props.items():
            cls._check_formula_prop(formulas.get(key), value_type_name, owner_props)
        cls._check_color(color)
        cls._check_icon(icon)
        WScalar.ensure_builtins()
        owner = WType.ensure(name, plural_name, embedded=embedded)
        for position, (key, value_type_name) in enumerate(props.items()):
            value_type_uuid, value_trait_uuid = cls._resolve_value_spec(value_type_name)
            _ = WProp.ensure(
                owner,
                key,
                None if value_type_uuid is None else WType.by_uuid(value_type_uuid),
                position,
                formulas.get(key),
                value_trait_uuid=value_trait_uuid,
            )
        row = types[owner.uuid]
        row.icon = icon
        row.color = color
        return cls._type_result(name)

    @classmethod
    @databasemethod(commit=True)
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
        enum_options.sync(owner.uuid, [(None, v) for v in (options or [])])
        row = types[owner.uuid]
        row.icon = icon
        row.color = color
        return cls._type_result(final_name)

    @classmethod
    @databasemethod(commit=True)
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
        enum_options.sync(owner.uuid, items)
        return cls._type_result(name)

    @classmethod
    @databasemethod(commit=True)
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
        unit_parts.sync(owner.uuid, final_name, items)
        row = types[owner.uuid]
        row.icon = icon
        row.color = color
        return cls._type_result(final_name)

    @classmethod
    @databasemethod(commit=True)
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
            and unit_parts.usage_count(owner.name) > 0
        ):
            raise ValidationError(
                f"unit {name!r} still has values; its base part cannot change"
            )
        unit_parts.sync(owner.uuid, owner.name, items)
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

    @classmethod
    @databasemethod(commit=True)
    def reorder_props(cls, type_name: str, keys: list[str]) -> Type:
        """Persist a new prop order; keys must cover the whole schema and
        keep the `name` prop first (see NAME_PROP_KEY)."""
        from nylium.server.errors import ValidationError

        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        if _is_builtin_type(owner):
            raise ValidationError(f"type {type_name!r} is builtin and cannot be edited")
        existing = [prop.key for prop in WProp.all_for(owner)]
        if set(keys) != set(existing):
            raise ValueError(f"prop order {keys!r} does not match {type_name!r} schema")
        if NAME_PROP_KEY in existing and (not keys or keys[0] != NAME_PROP_KEY):
            raise ValidationError(f"the {NAME_PROP_KEY!r} prop must stay first")
        WProp.reorder(owner, keys)
        return cls._type_result(type_name)

    @classmethod
    @databasemethod(commit=True)
    def sync_props(
        cls, type_name: str, items: list[tuple[UUID | None, str, str, str | None]]
    ) -> Type:
        """Apply the type editor's full prop draft at once. Each item is
        (uuid | None, key, value type name, formula | None): a matching
        uuid edits that prop in place (rename/retype — a retype purges
        the old values), None creates a new prop, props absent from the
        draft are deleted for every instance at once. The pinned `name`
        prop must keep its uuid, its key, its String type and the first
        position. A formula (ADR-0005) must be Numeric, or Integer for a
        bare COUNT."""
        from nylium.server.errors import ValidationError

        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        if _is_builtin_type(owner):
            raise ValidationError(f"type {type_name!r} is builtin and cannot be edited")
        existing = WProp.all_for(owner)
        by_uuid = {prop.uuid: prop for prop in existing}
        name_prop = next(
            (prop for prop in existing if prop.key == NAME_PROP_KEY), None
        )
        if not items:
            raise ValidationError("a type must keep at least its 'name' prop")
        first_uuid, first_key, first_type, _ = items[0]
        if (
            name_prop is not None
            and (first_uuid, first_key, first_type)
            != (name_prop.uuid, NAME_PROP_KEY, WString.TYPE_NAME)
        ):
            raise ValidationError(
                f"the {NAME_PROP_KEY!r} prop must stay first, keyed {NAME_PROP_KEY!r}, typed {WString.TYPE_NAME!r}"
            )
        keys = [key for _, key, _, _ in items]
        if any(not key.strip() for key in keys):
            raise ValidationError("prop keys must not be empty")
        for key in keys:
            cls._check_reserved_name(key, "prop key")
        if len(set(keys)) != len(keys):
            raise ValidationError(f"duplicate prop keys in {keys!r}")
        strangers = [uuid for uuid, _, _, _ in items if uuid is not None and uuid not in by_uuid]
        if strangers:
            raise ValidationError(f"prop uuids {strangers!r} do not belong to {type_name!r}")
        # ADR-0005 rename-rewrite, local pass: the editor echoes formulas
        # back verbatim, so a renamed key would otherwise fail validation
        # on the stale path. Rewrite array keys — and member keys of
        # self-referencing arrays — before checking against the new schema.
        renames = {
            by_uuid[uuid].key: key
            for uuid, key, _, _ in items
            if uuid is not None and by_uuid[uuid].key != key
        }
        self_arrays = {
            key
            for _, key, value_type_name, _ in items
            if WType.is_array_name(value_type_name)
            and WType.element_name(value_type_name) == type_name
        }
        if renames:
            items = [
                (
                    uuid,
                    key,
                    value_type_name,
                    Formula.rewrite(formula, renames, {k: renames for k in self_arrays})
                    if formula is not None
                    else None,
                )
                for uuid, key, value_type_name, formula in items
            ]
        owner_props = [(key, value_type_name) for _, key, value_type_name, _ in items]
        for _, _, value_type_name, formula in items:
            cls._check_formula_prop(formula, value_type_name, owner_props)
        resolved = [
            (uuid, key, *cls._resolve_value_spec(value_type_name), formula)
            for uuid, key, value_type_name, formula in items
        ]
        # cross-type pass: other types aggregate over Array<type_name>
        # props — rewrite their stored formulas to the new member keys, or
        # refuse the whole sync when a referenced member dies
        formula_updates = cls._rewrite_dependent_formulas(
            type_name, owner.uuid, owner_props, renames
        )
        # embedded children die with their prop: deleting or retyping an
        # embedded prop would cascade the link rows away and orphan the
        # child instances — destroy them while the prop still stands
        kept = {uuid: (key, vt) for uuid, key, vt, _, _ in resolved if uuid is not None}
        embedded_renamed = False
        for prop in existing:
            if prop.is_trait_bound:
                continue  # Any<…> has no concrete value type to compare
            old_value_type = prop.value_type()
            if not old_value_type.is_embedded:
                continue
            draft = kept.get(prop.uuid)
            if draft is None or draft[1] != old_value_type.uuid:
                WEmbedded.destroy_children_of_prop(prop.uuid)
            elif draft[0] != prop.key:
                embedded_renamed = True
        WProp.sync_schema(owner, resolved)
        for prop_uuid, rewritten in formula_updates:
            props[prop_uuid].formula = rewritten
        if embedded_renamed:
            # a renamed embedded prop key invalidates every generated
            # child name of every instance of this type
            for instance_uuid in [i.uuid for i in instances.where(type_uuid=owner.uuid)]:
                WEmbedded.regenerate_names(instance_uuid)
        return cls._type_result(type_name)

    @classmethod
    @databasemethod(commit=True)
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
        from nylium.server.errors import ValidationError

        owner = WType.by_name(name)
        if owner is None:
            raise KeyError(f"no type {name!r}")
        if _is_builtin_type(owner):
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
        row.plural_name = final_plural
        row.icon = final_icon
        row.color = final_color
        if owner.is_unit and final_name != name:
            # the parameterized Numeric<Unit> row tags along — prop value
            # types reference it by uuid, only the display name changes
            parameterized_row = next(
                types.where(name=WType.unit_numeric_name(name)), None
            )
            if parameterized_row is not None:
                parameterized_row.name = WType.unit_numeric_name(final_name)
                parameterized_row.plural_name = f"{WType.unit_numeric_name(final_name)}s"
        return cls._type_result(final_name)

    @classmethod
    @databasemethod(commit=True)
    def delete_type(cls, name: str) -> bool:
        """Refuses while instances exist; other types referencing this one
        as a prop value type are stopped by the FK, on purpose."""
        from nylium.server.errors import ValidationError

        owner = WType.by_name(name)
        if owner is None:
            return False
        if _is_builtin_type(owner):
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
                types.where(name=WType.unit_numeric_name(name)), None
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

    # --- objects ---

    # --- traits (ADR-0013) ---

    @classmethod
    @databasemethod(commit=False)
    def list_traits(cls) -> list[Trait]:
        return list(traits.all())

    @classmethod
    @databasemethod(commit=False)
    def get_trait(cls, name: str) -> Trait | None:
        return next(traits.where(name=name), None)

    @classmethod
    def _trait_result(cls, name: str) -> Trait:
        result = next(traits.where(name=name), None)
        if result is None:
            raise RuntimeError(f"trait {name!r} vanished after write")
        return result

    @classmethod
    @databasemethod(commit=True)
    def create_trait(
        cls, name: str, color: str, props: dict[str, str] | None = None
    ) -> Trait:
        """props maps key -> value spec (a concrete type name or
        Any<TraitName>). Dict order becomes the display order. Traits v1
        have no name prop and no formulas — they're prop bundles, not
        types."""
        from nylium.server.errors import ValidationError

        final_name = name.strip()
        if not final_name:
            raise ValidationError("trait name must not be empty")
        cls._check_reserved_name(final_name, "trait name")
        if WType.is_any_name(final_name):
            raise ValidationError(
                f"trait name {final_name!r} collides with the {WType.ANY_PREFIX}…> grammar"
            )
        if next(traits.where(name=final_name), None) is not None:
            raise ValueError(f"trait {final_name!r} already exists")
        cls._check_color(color)
        specs = dict(props or {})
        for key in specs:
            if not key.strip():
                raise ValidationError("prop keys must not be empty")
            cls._check_reserved_name(key, "prop key")
        WScalar.ensure_builtins()
        resolved: list[SchemaItem] = [
            (None, key, *cls._resolve_value_spec(spec), None)
            for key, spec in specs.items()
        ]
        trait = traits.create(final_name, color)
        WProp.sync_trait_schema(trait.uuid, resolved)
        return cls._trait_result(final_name)

    @classmethod
    @databasemethod(commit=True)
    def sync_trait(
        cls,
        name: str,
        new_name: str | None = None,
        color: str | None = None,
        items: list[tuple[UUID | None, str, str, str | None]] | None = None,
    ) -> Trait:
        """Edit a trait's identity and/or prop draft. items is the same
        (uuid | None, key, value spec, formula | None) shape as sync_props
        — traits v1 have no formulas, so the fourth element must be None.
        A retype/deleted prop purges values of every attached type's
        instances (inside sync_trait_schema)."""
        from nylium.server.errors import ValidationError

        row = next(traits.where(name=name), None)
        if row is None:
            raise KeyError(f"no trait {name!r}")
        final_name = name if new_name is None else new_name.strip()
        if not final_name:
            raise ValidationError("trait name must not be empty")
        cls._check_reserved_name(final_name, "trait name")
        if WType.is_any_name(final_name):
            raise ValidationError(
                f"trait name {final_name!r} collides with the {WType.ANY_PREFIX}…> grammar"
            )
        collision = next(traits.where(name=final_name), None)
        if collision is not None and collision.uuid != row.uuid:
            raise ValueError(f"trait {final_name!r} already exists")
        final_color = row.color if color is None else color
        if color is not None:
            cls._check_color(color)
        if items is not None:
            if not items:
                raise ValidationError(f"trait {name!r} must keep at least one prop")
            existing = {p.uuid for p in props.where(owner_trait_uuid=row.uuid)}
            keys = [key for _, key, _, _ in items]
            if any(not key.strip() for key in keys):
                raise ValidationError("prop keys must not be empty")
            for key in keys:
                cls._check_reserved_name(key, "prop key")
            if len(set(keys)) != len(keys):
                raise ValidationError(f"duplicate prop keys in {keys!r}")
            if any(formula is not None for _, _, _, formula in items):
                raise ValidationError("traits v1 have no formula props")
            strangers = [
                uuid for uuid, _, _, _ in items
                if uuid is not None and uuid not in existing
            ]
            if strangers:
                raise ValidationError(
                    f"prop uuids {strangers!r} do not belong to trait {name!r}"
                )
            resolved: list[SchemaItem] = [
                (uuid, key, *cls._resolve_value_spec(spec), None)
                for uuid, key, spec, _ in items
            ]
            WProp.sync_trait_schema(row.uuid, resolved)
        row.name = final_name
        row.color = final_color
        return cls._trait_result(final_name)

    @classmethod
    @databasemethod(commit=True)
    def delete_trait(cls, name: str) -> bool:
        """Refuses while the trait is attached to any type or used as an
        Any<> bound — the error names the dependents."""
        row = next(traits.where(name=name), None)
        if row is None:
            return False
        attached: list[str] = []
        for link in type_traits.where(trait_uuid=row.uuid):
            owner = types.get(link.type_uuid)
            attached.append("<gone>" if owner is None else owner.name)
        bound_owners: list[str] = []
        for p in props.where(value_trait_uuid=row.uuid):
            if p.owner_trait_uuid is not None:
                owner_trait = traits.get(p.owner_trait_uuid)
                bound_owners.append(
                    "<gone>" if owner_trait is None else f"trait {owner_trait.name}"
                )
            elif p.owner_type_uuid is not None:
                owner_type = types.get(p.owner_type_uuid)
                bound_owners.append(
                    "<gone>" if owner_type is None else f"type {owner_type.name}"
                )
        if attached or bound_owners:
            parts: list[str] = []
            if attached:
                parts.append(f"attached to {sorted(attached)!r}")
            if bound_owners:
                parts.append(
                    f"used as {WType.ANY_PREFIX}{name}> bound on {sorted(bound_owners)!r}"
                )
            raise ValueError(f"trait {name!r} is still " + " and ".join(parts))
        traits.delete(row.uuid)  # its props cascade
        return True

    @classmethod
    @databasemethod(commit=True)
    def attach_trait(cls, type_name: str, trait_name: str) -> Type:
        """Attach a trait to a user type. Prop keys must not collide with
        the type's current effective schema."""
        from nylium.server.errors import ValidationError

        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        if _is_builtin_type(owner):
            raise ValidationError(f"type {type_name!r} is builtin and cannot be edited")
        trait = next(traits.where(name=trait_name), None)
        if trait is None:
            raise KeyError(f"no trait {trait_name!r}")
        links = list(type_traits.where(type_uuid=owner.uuid))
        if any(link.trait_uuid == trait.uuid for link in links):
            raise ValueError(f"trait {trait_name!r} is already attached to {type_name!r}")
        taken = {p.key for p in WProp.effective_for(owner)}
        collisions = sorted({p.key for p in trait.props} & taken)
        if collisions:
            raise ValidationError(
                f"prop keys {collisions!r} of trait {trait_name!r} collide with {type_name!r}"
            )
        position = max((link.position for link in links), default=-1) + 1
        _ = type_traits.attach(owner.uuid, trait.uuid, position)
        return cls._type_result(type_name)

    @classmethod
    @databasemethod(commit=True)
    def detach_trait(cls, type_name: str, trait_name: str) -> Type:
        """Detach a trait; the trait prop values of this type's instances
        are purged (the trait itself and its other types keep theirs)."""
        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        trait = next(traits.where(name=trait_name), None)
        if trait is None:
            raise KeyError(f"no trait {trait_name!r}")
        link = next(
            (
                edge
                for edge in type_traits.where(type_uuid=owner.uuid)
                if edge.trait_uuid == trait.uuid
            ),
            None,
        )
        if link is None:
            raise KeyError(f"trait {trait_name!r} is not attached to {type_name!r}")
        inst_uuids = [i.uuid for i in instances.where(type_uuid=owner.uuid)]
        for p in props.where(owner_trait_uuid=trait.uuid):
            WProp.purge_values_for_instances(p.uuid, inst_uuids)
        type_traits.detach(owner.uuid, trait.uuid)
        return cls._type_result(type_name)


    @classmethod
    @databasemethod(commit=False)
    def list_objects(cls, type_name: str) -> list[ObjectView]:
        owner = WType.by_name(type_name)
        if owner is None:
            return []
        if owner.is_embedded:
            # composition children never list standalone (ADR-0004) —
            # this also keeps them out of every ref picker
            return []
        views = [
            ObjectView.from_uuid(uuid)
            for uuid in [i.uuid for i in instances.where(type_uuid=owner.uuid)]
        ]
        return [view for view in views if view is not None]

    @classmethod
    def get_object(cls, uuid: UUID) -> ObjectView | None:
        return ObjectView.from_uuid(uuid)

    @classmethod
    @databasemethod(commit=False)
    def export_markdown(cls, uuid: UUID) -> tuple[str, str] | None:
        """Render an object as a markdown document for download.

        Links to other objects render as `[label](object:<uuid>)` — the
        display name up front, the pointer kept in the href. Nothing is
        expanded recursively (a graph is not a tree). Returns
        (filename, content) or None when the object does not exist.
        """
        from nylium.api.markdown import render_object_markdown

        view = ObjectView.from_uuid(uuid)
        if view is None:
            return None

        def ref_label(ref: ObjectRef) -> str:
            wrapper = WObject.wrap(ref.uuid)
            label = cast(str | None, getattr(wrapper, NAME_PROP_KEY))
            if label:
                return label
            inst = instances.get(ref.uuid)
            return "" if inst is None else inst.name

        return render_object_markdown(view, ref_label)

    @classmethod
    @databasemethod(commit=True)
    def create_object(
        cls, type_name: str, props: dict[str, PropInput] | None = None
    ) -> ObjectView:
        from nylium.server.errors import ValidationError

        owner = WType.by_name(type_name)
        if owner is not None and owner.is_embedded:
            raise ValidationError(
                f"type {type_name!r} is embedded — its instances exist only as a prop value of an owner object"
            )
        normalized = cls._normalize_props(type_name, props or {})
        klass = WTypeMeta.python_class(type_name)
        if klass is not None:
            # **props forwarding: the dict can't collide with _uuid in
            # practice (prop keys), but the checker can't prove it
            ctor = cast(Callable[..., WObject], klass)
            instance_uuid = ctor(**normalized).uuid
        else:
            instance_uuid = WObject.create_db_only(type_name, normalized)
        # heal generated names: an embedded prop written before the name
        # prop in the same request computed a fallback-based child name
        WEmbedded.regenerate_names(instance_uuid)
        view = cls.get_object(instance_uuid)
        if view is None:
            raise RuntimeError(f"created {type_name} instance {instance_uuid} vanished")
        return view

    @classmethod
    @databasemethod(commit=True)
    def update_object(cls, uuid: UUID, props: dict[str, PropInput]) -> ObjectView:
        from nylium.server.errors import ValidationError

        if instances[uuid].owner_object_uuid is not None:
            raise ValidationError(
                "embedded objects are edited through their owner — write the embedded prop on the parent instead"
            )
        wrapper = WObject.wrap(uuid)
        type_name = instances[uuid].type_name
        normalized = cls._normalize_props(type_name, props)
        for key, value in normalized.items():
            setattr(wrapper, key, value)
        # a renamed parent (or a reordered draft) invalidates the
        # generated names of its embedded children
        WEmbedded.regenerate_names(uuid)
        view = cls.get_object(uuid)
        if view is None:
            raise RuntimeError(f"updated instance {uuid} vanished")
        return view

    # --- files (ADR-0006) ---

    @classmethod
    @databasemethod(commit=True)
    def create_file(
        cls, type_name: str, filename: str, mime: str, data: bytes
    ) -> File:
        """Atomic upload (ADR-0008): one transaction writes the `files` row,
        then the blob lands on disk last. If the disk write fails the
        transaction rolls back — no half-created pointer."""
        from nylium.server.errors import ValidationError

        if not WFile.is_file_type(type_name):
            raise ValidationError(
                f"type {type_name!r} is not a file type — use /api/files only for File/Document/Image"
            )
        if not filename.strip():
            raise ValidationError("filename must not be empty")
        if len(data) > WFile.MAX_UPLOAD_BYTES:
            raise ValidationError(
                f"file exceeds the {WFile.MAX_UPLOAD_BYTES // (1024 * 1024)} MiB upload cap"
            )
        if not WFile.accepts_mime(type_name, mime):
            raise ValidationError(
                f"{type_name} does not accept MIME {mime!r}"
            )
        file_uuid = uuid4()
        created = files.create(file_uuid, type_name, filename, mime, len(data))
        blob = WFile.blob_path(file_uuid)
        tmp = blob.with_suffix(".tmp")
        try:
            _ = tmp.write_bytes(data)
            _ = tmp.replace(blob)  # rename is atomic on the same filesystem
        finally:
            tmp.unlink(missing_ok=True)
        return created

    @classmethod
    @databasemethod(commit=False)
    def get_file(cls, uuid: UUID) -> File | None:
        return files.get(uuid)

    @classmethod
    @databasemethod(commit=False)
    def list_files(cls) -> list[File]:
        return list(files.values())

    @classmethod
    @databasemethod(commit=True)
    def rename_file(cls, uuid: UUID, name: str) -> File:
        """ADR-0008: rename is a display-name update — the uuid pointer is
        stable, so no reference ever breaks."""
        from nylium.server.errors import ValidationError

        if not name.strip():
            raise ValidationError("filename must not be empty")
        view = cls.get_file(uuid)
        if view is None:
            raise KeyError(f"no file {uuid}")
        view.name = name
        return view

    @classmethod
    @databasemethod(commit=True)
    def delete_file(cls, uuid: UUID) -> bool:
        """ADR-0008: drop the files row and the blob. An Image used as an
        icon resets every referencing type to the default glyph."""
        row = files.get(uuid)
        if row is None:
            return False
        if row.type_name == WFile.TYPE_IMAGE:
            WFile.reset_icons_referencing(uuid)
        WFile.clear_array_refs(uuid)
        files.delete(uuid)
        WFile.delete_blob(uuid)
        return True

    @classmethod
    def storage_stats(cls) -> dict[str, int]:
        """Disk usage of the volume that holds the blob store, plus
        nylium's own footprint (database + blobs). Read-only, no session
        needed — the size query goes through the engine directly."""
        import shutil

        from sqlalchemy import text

        from nylium.database import Database
        from nylium.objects.wfile import WFile

        storage = WFile.storage_dir()
        usage = shutil.disk_usage(storage)
        with Database.engine.connect() as connection:
            db_bytes = cast(
                int,
                connection.execute(
                    text("SELECT pg_database_size(current_database())")
                ).scalar_one(),
            )
        blob_bytes = sum(
            path.stat().st_size for path in storage.iterdir() if path.is_file()
        )
        return {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "nylium_bytes": db_bytes + blob_bytes,
        }

    @classmethod
    @databasemethod(commit=True)
    def delete_object(cls, uuid: UUID) -> bool:
        from nylium.server.errors import ValidationError

        inst = instances.get(uuid)
        if inst is None:
            return False
        if inst.owner_object_uuid is not None:
            raise ValidationError(
                "embedded objects are deleted with their owner or by clearing the prop that holds them"
            )
        WObject.wrap(uuid).delete()
        return True

    # --- functions (ADR-0007) ---

    @classmethod
    @databasemethod(commit=False)
    def list_functions(cls) -> list[FunctionView]:
        views = [FunctionView.from_uuid(uuid) for uuid in WFunction.instance_uuids()]
        return [view for view in views if view is not None]

    @classmethod
    @databasemethod(commit=False)
    def get_function(cls, uuid: UUID) -> FunctionView | None:
        return FunctionView.from_uuid(uuid)

    @classmethod
    @databasemethod(commit=True)
    def create_function(
        cls,
        input_type: str,
        output_type: str,
        name: str,
        input_object_uuid: UUID | None,
        nodes: list[tuple[UUID, str, int, Mapping[str, object]]],
        edges: list[tuple[UUID, int, UUID, int]],
    ) -> FunctionView:
        """Create a Function<T,R> instance: validate the DAG draft before
        anything persists, materialize the parameterized type, create the
        object (name + input link), then save the graph, index deps and
        refuse a cross-function cycle. `nodes` items are (uuid, kind,
        position, config) — client-generated uuids so edges can reference
        them; `edges` items are (from_node_uuid, from_port, to_node_uuid,
        to_port)."""
        from nylium.server.errors import ValidationError

        if not name.strip():
            raise ValidationError("function name must not be empty")
        cls._check_reserved_name(name, "function name")
        # validate the DAG before creating anything (fail-fast, no orphans)
        WFunction.validate_graph(
            [(uuid, kind, config) for uuid, kind, _, config in nodes],
            edges,
            input_type,
            output_type,
        )
        owner = WFunction.ensure_type(input_type, output_type)
        props: dict[str, PropInput] = {NAME_PROP_KEY: name}
        if input_object_uuid is not None:
            props[INPUT_PROP_KEY] = input_object_uuid
        view = cls.create_object(owner.name, props)
        WFunction.sync_graph(view.uuid, nodes, edges)
        WFunction.sync_deps(view.uuid)
        WFunction.assert_no_dependency_cycle()
        result = FunctionView.from_uuid(view.uuid)
        if result is None:
            raise RuntimeError(f"created function {view.uuid} vanished")
        return result

    @classmethod
    @databasemethod(commit=True)
    def update_function(
        cls,
        uuid: UUID,
        name: str,
        input_object_uuid: UUID | None,
        nodes: list[tuple[UUID, str, int, Mapping[str, object]]],
        edges: list[tuple[UUID, int, UUID, int]],
    ) -> FunctionView:
        """Replace a function's DAG and re-point its input in one draft.
        The declared input/output types are fixed (they parameterize the
        type); only the graph, name and input link change here."""
        from nylium.server.errors import ValidationError

        if not name.strip():
            raise ValidationError("function name must not be empty")
        existing = FunctionView.from_uuid(uuid)
        if existing is None:
            raise ValidationError(f"{uuid} is not a function instance")
        cls._check_reserved_name(name, "function name")
        WFunction.validate_graph(
            [(n_uuid, kind, config) for n_uuid, kind, _, config in nodes],
            edges,
            existing.input_type,
            existing.output_type,
        )
        props: dict[str, PropInput] = {NAME_PROP_KEY: name}
        if input_object_uuid is not None:
            props[INPUT_PROP_KEY] = input_object_uuid
        _ = cls.update_object(uuid, props)
        WFunction.sync_graph(uuid, nodes, edges)
        WFunction.sync_deps(uuid)
        WFunction.assert_no_dependency_cycle()
        result = FunctionView.from_uuid(uuid)
        if result is None:
            raise RuntimeError(f"updated function {uuid} vanished")
        return result

    @classmethod
    @databasemethod(commit=True)
    def delete_function(cls, uuid: UUID) -> bool:
        if FunctionView.from_uuid(uuid) is None:
            return False
        # unbind every prop computed through it first, then drop the object
        # (graph + deps cascade on the FK)
        for prop in props.where(function_uuid=uuid):
            prop.function_uuid = None
        return cls.delete_object(uuid)

    @classmethod
    @databasemethod(commit=True)
    def set_prop_function(
        cls, type_name: str, prop_key: str, function_uuid: UUID | None
    ) -> Type:
        """Bind a Function<T,R> instance to a prop (None unbinds). The
        function's output type must equal the prop's value type, and a
        formula-backed prop cannot become function-backed. Refuses a
        cross-function dependency cycle."""
        from nylium.server.errors import ValidationError

        owner = WType.by_name(type_name)
        if owner is None:
            raise KeyError(f"no type {type_name!r}")
        if _is_builtin_type(owner):
            raise ValidationError(f"type {type_name!r} is builtin and cannot be edited")
        prop = WProp.by_key(owner, prop_key)
        if prop is None:
            raise ValidationError(f"type {type_name!r} has no prop {prop_key!r}")
        if prop.is_trait_bound:
            raise ValidationError(
                f"prop {prop_key!r} is {WType.ANY_PREFIX}…>-bound and cannot run a function"
            )
        if function_uuid is not None:
            fn = FunctionView.from_uuid(function_uuid)
            if fn is None:
                raise ValidationError(f"{function_uuid} is not a function instance")
            if fn.output_type != prop.value_type().name:
                raise ValidationError(
                    f"function output {fn.output_type!r} does not match "
                    + f"prop type {prop.value_type().name!r}"
                )
        if prop.formula is not None:
            raise ValidationError(
                f"prop {prop_key!r} already has a formula — a prop cannot be both"
            )
        props[prop.uuid].function_uuid = function_uuid
        WFunction.assert_no_dependency_cycle()
        result = cls._type_result(type_name)
        return result

    # --- internals ---

    @classmethod
    def _member_props(cls, element_type_name: str) -> list[tuple[str, str]] | None:
        """The schema of an array's element type, for formula validation.
        None when the element type cannot be resolved at all."""
        element = WType.by_name(element_type_name)
        if element is None:
            return None
        # effective schema (ADR-0013); spec names keep Any<Trait> members
        # inspectable for formula validation
        return [
            (prop.key, prop.value_spec_name()) for prop in WProp.effective_for(element)
        ]

    @classmethod
    def _rewrite_dependent_formulas(
        cls,
        type_name: str,
        owner_uuid: UUID,
        new_schema: list[tuple[str, str]],
        renames: dict[str, str],
    ) -> list[tuple[UUID, str]]:
        """ADR-0005 rename-rewrite, cross-type pass: formulas on OTHER
        types that aggregate over ``Array<type_name>`` props are rewritten
        to the renamed member keys and re-validated against the new
        schema. A formula that still reads a deleted or retyped member
        fails the whole sync — schemas never strand a stored formula.
        Returns (prop uuid, new formula) updates; the caller persists
        them after the local schema change lands."""
        array_type_row = next(types.where(name=WType.array_name(type_name)), None)
        if array_type_row is None:
            return []

        def resolve_member_type(element_name: str) -> list[tuple[str, str]] | None:
            if element_name == type_name:
                return new_schema
            return cls._member_props(element_name)

        updates: list[tuple[UUID, str]] = []
        usages = [
            (p.owner_type_uuid, p.key)
            for p in props.where(value_type_uuid=array_type_row.uuid)
        ]
        by_owner: dict[UUID, list[str]] = {}
        for dependent_uuid, array_key in usages:
            # None: trait-owned array props carry no formulas to rewrite (v1)
            if dependent_uuid is None or dependent_uuid == owner_uuid:
                continue  # self-referencing arrays were rewritten locally
            by_owner.setdefault(dependent_uuid, []).append(array_key)
        for dependent_uuid, array_keys in by_owner.items():
            dependent = WType.by_uuid(dependent_uuid)
            if dependent is None:
                continue
            dependent_props = WProp.all_for(dependent)
            # spec names: a trait-bound prop has no concrete value type
            dependent_schema = [
                (prop.key, prop.value_spec_name()) for prop in dependent_props
            ]
            member_renames = {key: renames for key in array_keys}
            for prop in dependent_props:
                if prop.formula is None:
                    continue
                rewritten = Formula.rewrite(prop.formula, {}, member_renames)
                Formula.validate(rewritten, dependent_schema, resolve_member_type)
                if rewritten != prop.formula:
                    updates.append((prop.uuid, rewritten))
        return updates

    @classmethod
    def _check_formula_prop(
        cls,
        formula: str | None,
        value_type_name: str,
        owner_type_props: list[tuple[str, str]],
    ) -> None:
        """Validate a prop's formula (ADR-0005) against the owner schema.
        A formula prop must be Numeric — or Integer for a bare COUNT."""
        from nylium.server.errors import ValidationError

        if formula is None:
            return
        if value_type_name == WInteger.TYPE_NAME:
            if not Formula.is_bare_count(formula):
                raise ValidationError(
                    "an Integer formula prop must be a bare COUNT(<array>) call"
                )
        elif value_type_name != WNumeric.TYPE_NAME:
            raise ValidationError(
                f"a formula prop must be {WNumeric.TYPE_NAME} (or {WInteger.TYPE_NAME} for a bare COUNT), got {value_type_name!r}"
            )
        Formula.validate(formula, owner_type_props, cls._member_props)

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
            element = cls._ensure_value_type(WType.element_name(name))
            if element.is_embedded:
                raise ValidationError(
                    f"arrays of embedded type {element.name!r} are not supported yet"
                )
            return WType.ensure(name)
        resolved = WType.ensure(name)
        if resolved.is_unit:
            raise ValidationError(
                f"unit type {name!r} needs a numeric parameter: {WType.unit_numeric_name(name)}"
            )
        return resolved

    @classmethod
    def _resolve_value_spec(cls, name: str) -> tuple[UUID | None, UUID | None]:
        """ADR-0013: a prop's value spec is a concrete type name or
        `Any<TraitName>`. Returns (value_type_uuid, value_trait_uuid) —
        exactly one of the two. Any<> is a top-level form only in v1:
        nested inside Array<…>/Numeric<…> it is refused."""
        from nylium.server.errors import ValidationError

        trait_name = WType.any_trait_of(name)
        if trait_name is not None:
            trait = next(traits.where(name=trait_name), None)
            if trait is None:
                raise ValidationError(f"no trait {trait_name!r}")
            return None, trait.uuid
        if WType.ANY_PREFIX in name:
            raise ValidationError(
                f"{name!r}: {WType.ANY_PREFIX}…> is only allowed as a top-level prop type"
            )
        return cls._ensure_value_type(name).uuid, None

    @classmethod
    @databasemethod(commit=False)
    def _normalize_props(
        cls, type_name: str, prop_specs: dict[str, PropInput]
    ) -> dict[str, StoredValue]:
        """Callers hand links over as UUID/ObjectRef (that's all they have);
        the object layer wants WObject wrappers. Resolve by prop type."""
        owner_type_row = next(types.where(name=type_name), None)
        if owner_type_row is None:
            raise KeyError(f"no type {type_name!r}")
        # ADR-0013: the effective schema — attached traits' props are
        # writable through the object editor like the type's own
        owner_props = list(owner_type_row.props)
        formula_readonly = {p.key for p in owner_props if p.formula is not None}
        function_readonly = {p.key for p in owner_props if p.function_uuid is not None}
        result: dict[str, StoredValue] = {}
        for key, value in prop_specs.items():
            if key in formula_readonly:
                from nylium.server.errors import ValidationError

                raise ValidationError(
                    f"prop {key!r} of {type_name!r} is computed by a formula — it is read-only"
                )
            if key in function_readonly:
                from nylium.server.errors import ValidationError

                raise ValidationError(
                    f"prop {key!r} of {type_name!r} is computed by a function — it is read-only"
                )
            normalized = cls._normalize_value(
                value, _prop_value_type_name(owner_type_row.uuid, key)
            )
            if key == NAME_PROP_KEY and isinstance(normalized, str):
                # → would make a user-typed name indistinguishable from a
                # generated embedded one. Embedded children never pass
                # here — their names are written by WEmbedded directly.
                cls._check_reserved_name(normalized, "object name")
            result[key] = normalized
        return result

    @classmethod
    def _normalize_value(cls, value: PropInput, type_name: str) -> StoredValue:
        if WScalar.by_type_name(type_name) is not None:
            return cast(StoredValue, value)
        if WType.unit_param_of(type_name) is not None:
            return cast(StoredValue, value)  # Quantity; parts checked in setattr
        if WEnum.is_enum(type_name):
            return cast(StoredValue, value)  # membership checked in setattr
        if WFile.is_file_type(type_name):
            # ADR-0008: a file-typed prop holds a files.uuid — never an
            # object link. ObjectRef/UUID both normalize to the raw uuid.
            if value is None:
                return None
            if isinstance(value, ObjectRef):
                return value.uuid
            if isinstance(value, UUID):
                return value
            raise TypeError(
                f"file prop of type {type_name!r} takes a files.uuid, got {type(value).__name__}"
            )
        if WType.is_any_name(type_name):
            # ADR-0013: a trait-bound prop is a link; the bound itself is
            # enforced in setattr (WTypeMeta.check_trait_link)
            if value is None:
                return None
            if isinstance(value, ObjectRef):
                return WObject.wrap(value.uuid)
            if isinstance(value, UUID):
                return WObject.wrap(value)
            raise TypeError(
                f"trait-bound prop of type {type_name!r} takes an object reference, got {type(value).__name__}"
            )
        if WType.is_array_name(type_name):
            if not isinstance(value, list):
                raise TypeError(f"array prop takes list, got {type(value).__name__}")
            element_name = WType.element_name(type_name)
            return [cls._normalize_value(item, element_name) for item in value]
        resolved = WType.by_name(type_name)
        if resolved is not None and resolved.is_embedded:
            # composition: the value is an inline props draft, recursively
            # normalized against the embedded type's schema. A link
            # (UUID/ObjectRef) is refused — picking an existing object is
            # exactly what embedded props are not (ADR-0004).
            if value is None:
                return None
            if not isinstance(value, dict):
                raise TypeError(
                    f"embedded prop of type {type_name!r} takes an inline props draft, got {type(value).__name__}"
                )
            resolved_props = list(WProp.effective_for(resolved))
            formula_readonly = {p.key for p in resolved_props if p.formula is not None}
            function_readonly = {
                p.key for p in resolved_props if p.function_uuid is not None
            }
            for child_key in value:
                if child_key in formula_readonly:
                    from nylium.server.errors import ValidationError

                    raise ValidationError(
                        f"prop {child_key!r} of {type_name!r} is computed by a formula — it is read-only"
                    )
                if child_key in function_readonly:
                    from nylium.server.errors import ValidationError

                    raise ValidationError(
                        f"prop {child_key!r} of {type_name!r} is computed by a function — it is read-only"
                    )
            return {
                key: cls._normalize_value(item, _prop_value_type_name(resolved.uuid, key))
                for key, item in value.items()
            }
        if isinstance(value, ObjectRef):
            return WObject.wrap(value.uuid)
        if isinstance(value, UUID):
            return WObject.wrap(value)
        return cast(StoredValue, value)  # anything else fails in setattr

    @classmethod
    def _check_color(cls, color: str) -> None:
        """ADR-0005: type colors are stored as #RRGGBB hex; anything else
        (including the legacy named palette) is rejected at the boundary."""
        from nylium.server.errors import ValidationError

        if not WColor.HEX_RE.fullmatch(color):
            raise ValidationError(f"color must be #RRGGBB hex, got {color!r}")

    @classmethod
    def _check_icon(cls, icon: str) -> None:
        """ADR-0006: an icon is either a Material glyph name or
        `img:<uuid>` pointing at a live Image instance."""
        from nylium.objects.wfile import WFile
        from nylium.server.errors import ValidationError

        image_uuid = WFile.parse_icon_image(icon)
        if image_uuid is None:
            return
        if not WFile.image_file_exists(image_uuid):
            raise ValidationError(
                f"icon {icon!r} does not reference a live Image instance"
            )

    @classmethod
    def _check_reserved_name(cls, value: str, what: str) -> None:
        """The → separator of generated embedded names is reserved, so a
        generated name can never collide with a user-typed one."""
        from nylium.server.errors import ValidationError

        if EMBEDDED_NAME_SEPARATOR in value:
            raise ValidationError(
                f"{what} {value!r} must not contain {EMBEDDED_NAME_SEPARATOR!r} — reserved for generated embedded names"
            )
