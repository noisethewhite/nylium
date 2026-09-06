"""Display DTOs for the nylium API.

pydantic dataclasses with extra="ignore", the morebuttons convention:
they validate on construction and serialize straight to JSON later,
when FastAPI mounts the Api class.

File-level exception to one-class-per-file: these are peer view types
of the same facade, mirroring the type/object graph they render.
"""
from __future__ import annotations

from dataclasses import field
from decimal import Decimal
from typing import Self, cast
from uuid import UUID

import sqlalchemy as sqla
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass
from sqlalchemy.orm import aliased

from nylium.database import Database, databasemethod
from nylium.tables import (
    ArrayValues,
    EnumOptions,
    InstanceValues,
    Instances,
    Props,
    StringValues,
    Types,
    UnitParts,
)
from nylium.objects import WObject, WProp, WType
from nylium.objects.monthday import MonthDay, MonthDayTime
from nylium.objects.quantity import Quantity
from nylium.objects.wembedded import EMBEDDED_NAME_SEPARATOR
from nylium.objects.wenum import WEnum
from nylium.objects.wfile import WFile
from nylium.objects.wformula import Formula
from nylium.objects.wfunction import WFunction
from nylium.objects.wscalar import ScalarPayload, WInteger, WScalar
from nylium.objects.wtypemeta import StoredValue

_CONFIG = ConfigDict(extra="ignore")

# The object title prop, pinned first on every object type (see
# api.NAME_PROP_KEY). Tags derive the owner's display name from it.
NAME_PROP_KEY = "name"


# --- type schema views ---


@dataclass(config=_CONFIG)
class EnumOptionView:
    uuid: UUID
    value: str


@dataclass(config=_CONFIG)
class UnitPartView:
    uuid: UUID
    name: str
    multiplier: Decimal
    offset: Decimal
    is_base: bool


@dataclass(config=_CONFIG)
class PropView:
    uuid: UUID
    key: str
    value_type: str
    # ADR-0005: a formula over the owner's Array<T> props, or None for a
    # plain stored prop
    formula: str | None = None
    # ADR-0007: the Function<T,R> instance computing this prop, or None
    function_uuid: UUID | None = None


@dataclass(config=_CONFIG)
class TypeView:
    name: str
    plural_name: str | None
    icon: str
    color: str
    kind: str
    # ADR-0004: composition types instantiate only as a prop value of an
    # owner object — no standalone creation, hidden from lists/pickers
    embedded: bool
    enum_options: list[EnumOptionView]
    unit_parts: list[UnitPartView]
    props: list[PropView]

    @classmethod
    @databasemethod(commit=False)
    def from_name(cls, name: str) -> Self:
        owner = WType.by_name(name)
        if owner is None:
            raise KeyError(f"no type {name!r}")
        return cls(
            name=name,
            plural_name=owner.plural_name,
            icon=owner.icon,
            color=owner.color,
            kind=owner.kind,
            embedded=owner.is_embedded,
            enum_options=[
                EnumOptionView(uuid=option.uuid, value=option.value)
                for option in EnumOptions.list_for(owner.uuid)
            ],
            unit_parts=[
                UnitPartView(
                    uuid=part.uuid,
                    name=part.name,
                    multiplier=part.multiplier,
                    offset=part.offset,
                    is_base=part.is_base,
                )
                for part in UnitParts.list_for(owner.uuid)
            ],
            props=[
                PropView(
                    uuid=prop.uuid,
                    key=prop.key,
                    value_type=prop.value_type().name,
                    formula=prop.formula,
                    function_uuid=prop.function_uuid,
                )
                for prop in WProp.all_for(owner)
            ],
        )


# --- object data views ---


@dataclass(config=_CONFIG)
class ObjectRef:
    """A link target rendered for display: who it is, not its whole body."""

    uuid: UUID
    type_name: str


@dataclass(config=_CONFIG)
class ScalarValue:
    """None means the prop was never set. `unit` is the unit part name
    as entered for `Numeric<Unit>` props; absent everywhere else."""

    value: ScalarPayload | None
    unit: str | None = None


@dataclass(config=_CONFIG)
class RefValue:
    """None means the link was never set (or the target is gone)."""

    ref: ObjectRef | None


@dataclass(config=_CONFIG)
class ArrayValue:
    """None means the prop was never set; [] means set to empty."""

    items: list[PropValue] | None


@dataclass(config=_CONFIG)
class EmbeddedValue:
    """A composition child rendered inline (ADR-0004). uuid None means
    the prop was never filled — the child is created lazily on the first
    write. On input, props is the full child draft and uuid is ignored:
    create-vs-update is decided by the existing link, not the client."""

    uuid: UUID | None
    type_name: str
    props: dict[str, PropValue]


PropValue = ScalarValue | RefValue | ArrayValue | EmbeddedValue


# --- file views (ADR-0008) ---


@dataclass(config=_CONFIG)
class FileView:
    """A file entity (ADR-0008): a self-contained row in `files`, the
    bytes stream from disk separately. `uuid` is the stable pointer;
    `name` the renameable display name; `type_name` File/Document/Image."""

    uuid: UUID
    type_name: str
    name: str
    mime: str
    size_bytes: int


@dataclass(config=_CONFIG)
class FunctionNodeView:
    """One node of a function's action DAG (ADR-0007)."""

    uuid: UUID
    kind: str
    position: int
    config: dict[str, object]


@dataclass(config=_CONFIG)
class FunctionEdgeView:
    """A dataflow edge between two function nodes (ADR-0007)."""

    uuid: UUID
    from_node_uuid: UUID
    from_port: int
    to_node_uuid: UUID
    to_port: int


@dataclass(config=_CONFIG)
class FunctionView:
    """Snapshot of one Function<T,R> instance: its parameterization, its
    input link, and its full action DAG (nodes + edges)."""

    uuid: UUID
    name: str
    type_name: str
    input_type: str
    output_type: str
    input_object_uuid: UUID | None
    nodes: list[FunctionNodeView]
    edges: list[FunctionEdgeView]

    @classmethod
    @databasemethod(commit=False)
    def from_uuid(cls, uuid: UUID) -> Self | None:
        type_uuid = Instances.type_uuid_of(uuid)
        if type_uuid is None:
            return None
        owner = WType.by_uuid(type_uuid)
        if owner is None or not owner.is_function:
            return None
        params = WType.function_params(owner.name)
        if params is None:
            return None
        input_type, output_type = params
        wrapper = WObject.wrap(uuid)
        name = cast(str | None, getattr(wrapper, NAME_PROP_KEY)) or Instances.name_of(uuid)
        return cls(
            uuid=uuid,
            name=name,
            type_name=owner.name,
            input_type=input_type,
            output_type=output_type,
            input_object_uuid=WFunction.input_object_uuid(uuid),
            nodes=[
                FunctionNodeView(
                    uuid=node.uuid,
                    kind=node.kind,
                    position=node.position,
                    config=node.config,
                )
                for node in WFunction.nodes(uuid)
            ],
            edges=[
                FunctionEdgeView(
                    uuid=edge.uuid,
                    from_node_uuid=edge.from_node_uuid,
                    from_port=edge.from_port,
                    to_node_uuid=edge.to_node_uuid,
                    to_port=edge.to_port,
                )
                for edge in WFunction.edges(uuid)
            ],
        )


@dataclass(config=_CONFIG)
class TagView:
    """A derived tag (ADR-0005): one array-membership edge projected back
    onto the member object. Nothing is stored — the name is recomputed on
    every read from the owner's display name and the prop key."""

    owner_uuid: UUID
    owner_name: str
    prop_key: str
    name: str
    # ADR-0005: tag color = the owner type's color, projected along so the
    # UI paints chips without a second fetch
    color: str


@dataclass(config=_CONFIG)
class ObjectView:
    """Snapshot of one instance: every prop rendered as a typed
    ScalarValue / RefValue / ArrayValue — no Any escapes. `tags` is the
    ADR-0005 reverse projection of the arrays that contain this object."""

    uuid: UUID
    type_name: str
    props: dict[str, PropValue]
    tags: list[TagView] = field(default_factory=list)

    @classmethod
    @databasemethod(commit=False)
    def from_uuid(cls, uuid: UUID) -> Self | None:
        type_uuid = Instances.type_uuid_of(uuid)
        if type_uuid is None:
            return None
        owner = WType.by_uuid(type_uuid)
        if owner is None:
            raise RuntimeError(f"instance {uuid} has dangling type")
        wrapper = WObject.wrap(uuid)
        props = {
            prop.key: cls._eval_function(prop)
            if prop.function_uuid is not None
            else cls._eval_formula(wrapper, prop)
            if prop.formula is not None
            else cls._render_prop(
                cast(StoredValue, getattr(wrapper, prop.key)),
                prop.value_type().name,
            )
            for prop in WProp.all_for(owner)
        }
        return cls(
            uuid=uuid,
            type_name=owner.name,
            props=props,
            tags=cls._tags_for(uuid, owner.name),
        )

    @classmethod
    @databasemethod(commit=False)
    def _tags_for(cls, uuid: UUID, type_name: str) -> list[TagView]:
        """ADR-0005: reverse-projection of array membership. Every
        ``Array<type_name>`` prop whose stored array contains this object
        becomes one tag ``<owner display name> → <prop key>``. One query,
        no N+1."""
        name_prop = aliased(Props)
        owner_types = aliased(Types)
        rows = Database.session.execute(
            sqla.select(
                InstanceValues.inst_uuid,  # owner object uuid
                Props.key,  # array prop key
                Instances.name,  # owner registry name (fallback title)
                StringValues.value,  # owner's `name` prop value (display title)
                owner_types.color,  # owner type's color paints the chip
            )
            .select_from(ArrayValues)
            .join(InstanceValues, InstanceValues.uuid == ArrayValues.inst_uuid)
            .join(Props, Props.uuid == InstanceValues.prop_uuid)
            .join(Types, Types.uuid == Props.value_type_uuid)
            .join(Instances, Instances.uuid == InstanceValues.inst_uuid)
            .join(owner_types, owner_types.uuid == Instances.type_uuid)
            .join(name_prop, name_prop.owner_type_uuid == Instances.type_uuid)
            .join(
                StringValues,
                sqla.and_(
                    StringValues.inst_uuid == Instances.uuid,
                    StringValues.prop_uuid == name_prop.uuid,
                ),
                isouter=True,
            )
            .where(
                ArrayValues.value_uuid == uuid,
                Types.name == WType.array_name(type_name),
                name_prop.key == NAME_PROP_KEY,
            )
            .distinct()
        ).all()
        tags: list[TagView] = []
        for row in rows:
            owner_uuid = cast(UUID, row[0])
            prop_key = cast(str, row[1])
            registry_name = cast(str, row[2])
            display_name = cast(str | None, row[3]) or registry_name
            color = cast(str, row[4])
            tags.append(
                TagView(
                    owner_uuid=owner_uuid,
                    owner_name=display_name,
                    prop_key=prop_key,
                    name=f"{display_name} {EMBEDDED_NAME_SEPARATOR} {prop_key}",
                    color=color,
                )
            )
        tags.sort(key=lambda tag: (tag.owner_name, tag.prop_key))
        return tags

    @classmethod
    @databasemethod(commit=False)
    def _eval_function(cls,  prop: WProp) -> ScalarValue:
        """ADR-0007 read-time evaluation: fold the function's DAG over its
        current input object. A div-by-zero / missing input renders empty."""
        assert prop.function_uuid is not None
        value = WFunction.evaluate_for(prop.function_uuid)
        return ScalarValue(value=value)

    @classmethod
    @databasemethod(commit=False)
    def _eval_formula(cls, wrapper: WObject, prop: WProp) -> ScalarValue:
        """ADR-0005 read-time evaluation: fold the stored formula over the
        live rows of the arrays it references. Unset cells count as 0; a
        dangling member keeps its stored row (COUNT sees it, the numeric
        aggregates treat it as 0). Division by zero renders empty."""
        assert prop.formula is not None
        refs = Formula.references(prop.formula)
        arrays: dict[str, list[dict[str, Decimal | None]]] = {}
        for array_key in {key for key, _ in refs}:
            members = cast(list[WObject] | None, getattr(wrapper, array_key)) or []
            existing: set[UUID] = (
                set(
                    Database.session.scalars(
                        sqla.select(Instances.uuid).where(
                            Instances.uuid.in_([member.uuid for member in members])
                        )
                    ).all()
                )
                if members
                else set()
            )
            wanted = {member for key, member in refs if key == array_key and member}
            rows: list[dict[str, Decimal | None]] = []
            for member in members:
                if member.uuid not in existing:
                    rows.append({})
                    continue
                row: dict[str, Decimal | None] = {}
                for key in wanted:
                    value = cast(StoredValue, getattr(member, key))
                    if isinstance(value, bool):
                        row[key] = None
                    elif isinstance(value, (int, Decimal)):
                        row[key] = Decimal(value)
                    elif isinstance(value, Quantity):
                        row[key] = value.value
                    else:
                        row[key] = None
                rows.append(row)
            arrays[array_key] = rows
        result = Formula.evaluate(prop.formula, arrays)
        if result is None:
            return ScalarValue(value=None)
        if prop.value_type().name == WInteger.TYPE_NAME:
            return ScalarValue(value=int(result))
        return ScalarValue(value=result)

    @classmethod
    @databasemethod(commit=False)
    def _render_prop(cls, value: StoredValue, type_name: str) -> PropValue:
        """The declared prop type disambiguates None: an unset scalar,
        an unset link and an unset array are three different views."""
        if WScalar.by_type_name(type_name) is not None:
            # year-less calendar values cross the wire as their stamps
            if isinstance(value, (MonthDay, MonthDayTime)):
                return ScalarValue(value=str(value))
            return ScalarValue(value=cast(ScalarPayload | None, value))
        if WType.unit_param_of(type_name) is not None:
            # Quantity: canonical magnitude re-scaled to the entered part,
            # rendered with the part name attached
            if value is None:
                return ScalarValue(value=None)
            if not isinstance(value, Quantity):
                raise TypeError(f"unit prop rendered a {type(value).__name__}")
            return ScalarValue(value=value.value, unit=value.unit)
        if WEnum.is_enum(type_name):
            return ScalarValue(value=cast(str | None, value))
        if WFile.is_file_type(type_name):
            # ADR-0008: a file-typed prop renders as a ref to the files row
            # — the uuid is the pointer, the type name is the declared one
            if value is None:
                return RefValue(ref=None)
            if not isinstance(value, UUID):
                raise TypeError(f"file prop rendered a {type(value).__name__}")
            return RefValue(ref=ObjectRef(uuid=value, type_name=type_name))
        if WType.is_array_name(type_name):
            element_name = WType.element_name(type_name)
            if value is None:
                return ArrayValue(items=None)
            if not isinstance(value, list):
                raise TypeError(f"array prop rendered a {type(value).__name__}")
            return ArrayValue(
                items=[cls._render_prop(item, element_name) for item in value]
            )
        owner = WType.by_name(type_name)
        if owner is not None and owner.is_embedded:
            # composition child: rendered as the full nested props view,
            # so the editor can inline its fields without a second fetch
            if value is None:
                return EmbeddedValue(uuid=None, type_name=type_name, props={})
            if not isinstance(value, WObject):
                raise TypeError(f"embedded prop rendered a {type(value).__name__}")
            child = ObjectView.from_uuid(value.uuid)
            if child is None:
                raise RuntimeError(f"embedded child {value.uuid} vanished")
            return EmbeddedValue(uuid=child.uuid, type_name=type_name, props=child.props)
        if value is None:
            return RefValue(ref=None)
        if not isinstance(value, WObject):
            raise TypeError(f"link prop rendered a {type(value).__name__}")
        return RefValue(
            ref=ObjectRef(uuid=value.uuid, type_name=Instances.get_type_name(value.uuid))
        )
