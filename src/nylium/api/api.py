"""Api: classmethod facade over the object layer — CRUD on types and
objects, returning the dataclass views from views.py.

This is the seam a future HTTP app (FastAPI) mounts. It never leaks
WObject wrappers or SQLAlchemy rows to callers: everything in and out
is a view, a UUID, or a plain python value. Writes go through the
WObject layer, so all type validation applies here too.

Table access lives on the table classes themselves (Types/TABLE_Instances/
TABLE_Props helpers); this file only orchestrates and adapts caller input.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import TypeAlias, cast
from uuid import UUID, uuid4

from nylium.api.views import FileView, FunctionView, ObjectRef, ObjectView, TypeView
from nylium.database import databasemethod
from nylium.tables.types import types
from nylium.tables import (
    TABLE_EnumOptions,
    TABLE_Files,
    TABLE_UnitParts,
    instances,
    props,
)
from nylium.objects.wembedded import EMBEDDED_NAME_SEPARATOR, WEmbedded
from nylium.objects.wenum import WEnum
from nylium.objects.wfile import WFile
from nylium.objects.wformula import Formula
from nylium.objects.wfunction import INPUT_PROP_KEY, WFunction
from nylium.objects.wobject import WObject
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import WColor, WInteger, WNumeric, WScalar, WString
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue, WTypeMeta


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
    def list_types(cls) -> list[TypeView]:
        return [TypeView.from_name(t.name) for t in types.all()]

    @classmethod
    @databasemethod(commit=False)
    def get_type(cls, name: str) -> TypeView | None:
        if WType.by_name(name) is None:
            return None
        return TypeView.from_name(name)

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
    ) -> TypeView:
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
            _ = WProp.ensure(
                owner,
                key,
                cls._ensure_value_type(value_type_name),
                position,
                formulas.get(key),
            )
        types.update(owner.uuid, owner.name, owner.plural_name, icon, color)
        return TypeView.from_name(name)

    @classmethod
    @databasemethod(commit=True)
    def create_enum(
        cls,
        name: str,
        options: list[str] | None = None,
        icon: str = "lists",
        color: str = WColor.DEFAULT,
    ) -> TypeView:
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
        TABLE_EnumOptions.sync(owner.uuid, [(None, v) for v in (options or [])])
        types.update(owner.uuid, owner.name, None, icon, color)
        return TypeView.from_name(final_name)

    @classmethod
    @databasemethod(commit=True)
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
        TABLE_EnumOptions.sync(owner.uuid, items)
        return TypeView.from_name(name)

    @classmethod
    @databasemethod(commit=True)
    def create_unit(
        cls,
        name: str,
        base: str,
        secondaries: list[tuple[str, Decimal, Decimal]] | None = None,
        icon: str = "straighten",
        color: str = WColor.DEFAULT,
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
        cls._check_reserved_name(final_name, "unit name")
        cls._check_color(color)
        cls._check_icon(icon)
        owner = WType.ensure(final_name, kind=WType.KIND_UNIT)
        items: list[tuple[UUID | None, str, Decimal, Decimal, bool]] = [
            (None, base_name, Decimal(1), Decimal(0), True),
            *[(None, n, m, o, False) for n, m, o in (secondaries or [])],
        ]
        cls._validate_unit_draft(items)
        TABLE_UnitParts.sync(owner.uuid, final_name, items)
        types.update(owner.uuid, owner.name, None, icon, color)
        return TypeView.from_name(final_name)

    @classmethod
    @databasemethod(commit=True)
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
        old_base = TABLE_UnitParts.base_of(owner.uuid)
        new_base_uuid = next(uuid for uuid, _, _, _, is_base in items if is_base)
        if (
            old_base is not None
            and new_base_uuid != old_base.uuid
            and TABLE_UnitParts.usage_total(owner.name) > 0
        ):
            raise ValidationError(
                f"unit {name!r} still has values; its base part cannot change"
            )
        TABLE_UnitParts.sync(owner.uuid, owner.name, items)
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
    @databasemethod(commit=True)
    def reorder_props(cls, type_name: str, keys: list[str]) -> TypeView:
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
        return TypeView.from_name(type_name)

    @classmethod
    @databasemethod(commit=True)
    def sync_props(
        cls, type_name: str, items: list[tuple[UUID | None, str, str, str | None]]
    ) -> TypeView:
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
        resolved: list[tuple[UUID | None, str, UUID, str | None]] = [
            (uuid, key, cls._ensure_value_type(value_type_name).uuid, formula)
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
        kept = {uuid: (key, vt) for uuid, key, vt, _ in resolved if uuid is not None}
        embedded_renamed = False
        for prop in existing:
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
            props.update_formula(prop_uuid, rewritten)
        if embedded_renamed:
            # a renamed embedded prop key invalidates every generated
            # child name of every instance of this type
            for instance_uuid in instances.by_type(owner.uuid):
                WEmbedded.regenerate_names(instance_uuid)
        return TypeView.from_name(type_name)

    @classmethod
    @databasemethod(commit=True)
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
        if _is_builtin_type(owner):
            raise ValidationError(f"type {name!r} is builtin and cannot be renamed")
        final_name = name if new_name is None else new_name.strip()
        if not final_name:
            raise ValidationError("type name must not be empty")
        cls._check_reserved_name(final_name, "type name")
        collision_row = types.by_name(final_name)
        if collision_row is not None and collision_row.uuid != owner.uuid:
            raise ValueError(f"type {final_name!r} already exists")
        final_plural = owner.plural_name if plural_name is None else plural_name
        if icon is not None:
            cls._check_icon(icon)
        final_icon = owner.icon if icon is None else icon
        if color is not None:
            cls._check_color(color)
        final_color = owner.color if color is None else color
        types.update(owner.uuid, final_name, final_plural, final_icon, final_color)
        if owner.is_unit and final_name != name:
            # the parameterized Numeric<Unit> row tags along — prop value
            # types reference it by uuid, only the display name changes
            parameterized_row = types.by_name(WType.unit_numeric_name(name))
            if parameterized_row is not None:
                parameterized = WType.by_uuid(parameterized_row.uuid)
                if parameterized is not None:
                    types.update(
                        parameterized_row.uuid,
                        WType.unit_numeric_name(final_name),
                        None,
                        parameterized.icon,
                        parameterized.color,
                    )
        return TypeView.from_name(final_name)

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
        instance_count = instances.count_of_type(owner.uuid)
        if instance_count:
            raise ValueError(
                f"type {name!r} still has {instance_count} instances"
            )
        if owner.is_unit:
            # refuse while any prop is parameterized on this unit, then
            # drop the orphaned parameterized row with the unit itself
            parameterized_row = types.by_name(WType.unit_numeric_name(name))
            if parameterized_row is not None:
                refs = props.count_with_value_type(parameterized_row.uuid)
                if refs:
                    raise ValueError(
                        f"unit {name!r} still parameterizes {refs} props"
                    )
                types.delete(parameterized_row.uuid)
        types.delete(owner.uuid)
        return True

    # --- objects ---

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
            for uuid in instances.by_type(owner.uuid)
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
            return label or instances.name_of(ref.uuid)

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

        if instances.owner_of(uuid) is not None:
            raise ValidationError(
                "embedded objects are edited through their owner — write the embedded prop on the parent instead"
            )
        wrapper = WObject.wrap(uuid)
        type_name = instances.get_type_name(uuid)
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
    ) -> FileView:
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
        TABLE_Files.create(file_uuid, type_name, filename, mime, len(data))
        blob = WFile.blob_path(file_uuid)
        tmp = blob.with_suffix(".tmp")
        try:
            _ = tmp.write_bytes(data)
            _ = tmp.replace(blob)  # rename is atomic on the same filesystem
        finally:
            tmp.unlink(missing_ok=True)
        return FileView(
            uuid=file_uuid, type_name=type_name, name=filename,
            mime=mime, size_bytes=len(data),
        )

    @classmethod
    @databasemethod(commit=False)
    def get_file(cls, uuid: UUID) -> FileView | None:
        row = TABLE_Files.by_uuid(uuid)
        if row is None:
            return None
        return FileView(
            uuid=row.uuid, type_name=row.type_name, name=row.name,
            mime=row.mime, size_bytes=row.size_bytes,
        )

    @classmethod
    @databasemethod(commit=False)
    def list_files(cls) -> list[FileView]:
        return [
            FileView(
                uuid=row.uuid, type_name=row.type_name, name=row.name,
                mime=row.mime, size_bytes=row.size_bytes,
            )
            for row in TABLE_Files.list_all()
        ]

    @classmethod
    @databasemethod(commit=True)
    def rename_file(cls, uuid: UUID, name: str) -> FileView:
        """ADR-0008: rename is a display-name update — the uuid pointer is
        stable, so no reference ever breaks."""
        from nylium.server.errors import ValidationError

        if not name.strip():
            raise ValidationError("filename must not be empty")
        TABLE_Files.rename(uuid, name)
        view = cls.get_file(uuid)
        if view is None:
            raise KeyError(f"no file {uuid}")
        return view

    @classmethod
    @databasemethod(commit=True)
    def delete_file(cls, uuid: UUID) -> bool:
        """ADR-0008: drop the files row and the blob. An Image used as an
        icon resets every referencing type to the default glyph."""
        row = TABLE_Files.by_uuid(uuid)
        if row is None:
            return False
        if row.type_name == WFile.TYPE_IMAGE:
            WFile.reset_icons_referencing(uuid)
        WFile.clear_array_refs(uuid)
        TABLE_Files.delete_by_uuid(uuid)
        WFile.delete_blob(uuid)
        return True

    @classmethod
    @databasemethod(commit=True)
    def delete_object(cls, uuid: UUID) -> bool:
        from nylium.server.errors import ValidationError

        if not instances.exists(uuid):
            return False
        if instances.owner_of(uuid) is not None:
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
        props.clear_function_references(uuid)
        return cls.delete_object(uuid)

    @classmethod
    @databasemethod(commit=True)
    def set_prop_function(
        cls, type_name: str, prop_key: str, function_uuid: UUID | None
    ) -> TypeView:
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
        props.set_function(prop.uuid, function_uuid)
        WFunction.assert_no_dependency_cycle()
        result = TypeView.from_name(type_name)
        return result

    # --- internals ---

    @classmethod
    def _member_props(cls, element_type_name: str) -> list[tuple[str, str]] | None:
        """The schema of an array's element type, for formula validation.
        None when the element type cannot be resolved at all."""
        element = WType.by_name(element_type_name)
        if element is None:
            return None
        return [(prop.key, prop.value_type().name) for prop in WProp.all_for(element)]

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
        array_type_row = types.by_name(WType.array_name(type_name))
        if array_type_row is None:
            return []

        def resolve_member_type(element_name: str) -> list[tuple[str, str]] | None:
            if element_name == type_name:
                return new_schema
            return cls._member_props(element_name)

        updates: list[tuple[UUID, str]] = []
        usages = props.usages_of_value_type(array_type_row.uuid)
        by_owner: dict[UUID, list[str]] = {}
        for dependent_uuid, array_key in usages:
            if dependent_uuid == owner_uuid:
                continue  # self-referencing arrays were rewritten locally
            by_owner.setdefault(dependent_uuid, []).append(array_key)
        for dependent_uuid, array_keys in by_owner.items():
            dependent = WType.by_uuid(dependent_uuid)
            if dependent is None:
                continue
            dependent_props = WProp.all_for(dependent)
            dependent_schema = [
                (prop.key, prop.value_type().name) for prop in dependent_props
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
    @databasemethod(commit=False)
    def _normalize_props(
        cls, type_name: str, prop_specs: dict[str, PropInput]
    ) -> dict[str, StoredValue]:
        """Callers hand links over as UUID/ObjectRef (that's all they have);
        the object layer wants WObject wrappers. Resolve by prop type."""
        owner_type_row = types.by_name(type_name)
        if owner_type_row is None:
            raise KeyError(f"no type {type_name!r}")
        formula_readonly = props.formula_keys(owner_type_row.uuid)
        function_readonly = props.function_keys(owner_type_row.uuid)
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
                value, props.get_type_name(owner_type_row.uuid, key)
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
            formula_readonly = props.formula_keys(resolved.uuid)
            function_readonly = props.function_keys(resolved.uuid)
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
                key: cls._normalize_value(item, props.get_type_name(resolved.uuid, key))
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
