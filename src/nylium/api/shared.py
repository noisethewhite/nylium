"""Cross-domain invariants and value normalization shared by every Api mixin
(ADR-0015)."""
from __future__ import annotations

from typing import ClassVar, TypeAlias, cast
from uuid import UUID

from nylium.api.display import ObjectRef
from nylium.database import Database
from nylium.tables.objects import Trait, traits
from nylium.tables.objects.types import Type, types
from nylium.objects.wembedded import EMBEDDED_NAME_SEPARATOR
from nylium.objects.wenum import WEnum
from nylium.objects.wfile import WFile
from nylium.objects.wobject import WObject
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import WColor, WScalar
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue

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


class ApiShared:
    @classmethod
    def _prop_value_type_name(cls, owner_type_uuid: UUID, key: str) -> str:
        """The value-spec name of one effective prop — what `_normalize_value`
        needs. ADR-0013: the effective schema includes attached traits' props."""
        owner = types.get(owner_type_uuid)
        if owner is None:
            raise KeyError(f"type <gone> has no prop {key!r}")
        prop = next((p for p in owner.props if p.key == key), None)
        if prop is None:
            raise KeyError(f"type {owner.name!r} has no prop {key!r}")
        return prop.value_type

    @classmethod
    def _is_builtin_type(cls, owner: WType) -> bool:
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

    # Marker for a polymorphic `Any<Trait>` prop link: a concrete target
    # can't be resolved statically, so it contributes one step and stops.
    _ANY_LINK: ClassVar[str] = "*"

    @classmethod
    def reference_levels(cls, rows: list[Type]) -> dict[str, int]:
        """Depth of each object type's longest reference chain.

        A type with no object links is level 1; a type linking to a
        level-N type is N+1. `Array<T>` counts as a link to T, `Any<Trait>`
        as one step without recursing. Embedded types participate as full
        nodes: they link to other types and other types link to them
        (ReceiptItem -> Product, Receipt -> Array<ReceiptItem>). Cycles are
        broken at first revisit. Each aggregate navigation opens its own
        session, so this is callable with or without an active one.

        Lives here, not on WType, for the same reason as `_is_builtin_type`:
        excluding scalars from the object graph needs WScalar.
        """
        object_names = {
            row.name
            for row in rows
            if row.kind == WType.KIND_OBJECT
            and not WScalar.is_scalar(row.name)
            and WType.unit_param_of(row.name) is None
            and not WType.is_array_name(row.name)
            and not WType.is_function_name(row.name)
        }
        links: dict[str, list[str | None]] = {}
        for row in rows:
            if row.name not in object_names:
                continue
            deps: list[str | None] = []
            for prop in row.props:
                value_type = prop.value_type
                if WType.is_any_name(value_type):
                    deps.append(cls._ANY_LINK)
                elif WType.is_array_name(value_type):
                    element = WType.element_name(value_type)
                    if element in object_names:
                        deps.append(element)
                elif value_type in object_names:
                    deps.append(value_type)
            links[row.name] = deps
        level: dict[str, int] = {}
        visiting: set[str] = set()

        def depth(name: str) -> int:
            cached = level.get(name)
            if cached is not None:
                return cached
            if name in visiting:
                return 0  # reference cycle — stop deepening this branch
            visiting.add(name)
            best = 0
            for dep in links.get(name, ()):
                if dep is None or dep == cls._ANY_LINK:
                    best = max(best, 1)
                else:
                    best = max(best, depth(dep))
            visiting.discard(name)
            result = 1 + best
            level[name] = result
            return result

        for name in links:
            _ = depth(name)
        return level

    @classmethod
    def _type_result(cls, name: str) -> Type:
        """Re-read a type the caller just wrote, for the return value.
        The write path resolves the name first, so a miss means a bug."""
        result = next(types.where(name=name), None)
        if result is None:
            raise RuntimeError(f"type {name!r} vanished after write")
        return result

    @classmethod
    def _trait_result(cls, name: str) -> Trait:
        result = next(traits.where(name=name), None)
        if result is None:
            raise RuntimeError(f"trait {name!r} vanished after write")
        return result

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
    @Database.use_same_session
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
        collect_readonly = {p.key for p in owner_props if p.collect is not None}
        result: dict[str, StoredValue] = {}
        for key, value in prop_specs.items():
            if key in formula_readonly:
                from nylium.server.errors import ValidationError

                raise ValidationError(
                    f"prop {key!r} of {type_name!r} is computed by a formula — it is read-only"
                )
            if key in collect_readonly:
                from nylium.server.errors import ValidationError

                raise ValidationError(
                    f"prop {key!r} of {type_name!r} is computed by collect — it is read-only"
                )
            normalized = cls._normalize_value(
                value, cls._prop_value_type_name(owner_type_row.uuid, key)
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
            if value is None:
                return None  # None unsets; [] is an empty array
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
            collect_readonly = {p.key for p in resolved_props if p.collect is not None}
            for child_key in value:
                if child_key in formula_readonly:
                    from nylium.server.errors import ValidationError

                    raise ValidationError(
                        f"prop {child_key!r} of {type_name!r} is computed by a formula — it is read-only"
                    )
                if child_key in collect_readonly:
                    from nylium.server.errors import ValidationError

                    raise ValidationError(
                        f"prop {child_key!r} of {type_name!r} is computed by collect — it is read-only"
                    )
            return {
                key: cls._normalize_value(
                    item, cls._prop_value_type_name(resolved.uuid, key)
                )
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
