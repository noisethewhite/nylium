"""Display DTOs for the nylium API — only the genuinely API-shaped
aggregates (ADR-0011 §5): the PropValue union, ObjectRef, the
tag/function projections and ObjectView. The per-table DTOs folded
into the table-domain objects, which serialize themselves via wire().

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
    TABLE_ArrayValues,
    TABLE_InstanceValues,
    TABLE_Instances,
    TABLE_Props,
    TABLE_StringValues,
    instances,
)
from nylium.tables.types import TABLE_Types
from nylium.objects import WObject, WType
from nylium.objects.monthday import MonthDay, MonthDayTime
from nylium.objects.quantity import Quantity
from nylium.objects.wembedded import EMBEDDED_NAME_SEPARATOR
from nylium.objects.wenum import WEnum
from nylium.objects.wfile import WFile
from nylium.objects.wformula import Formula
from nylium.objects.wfunction import WFunction
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import ScalarPayload, WInteger, WScalar
from nylium.objects.wtypemeta import StoredValue

_CONFIG = ConfigDict(extra="ignore")

# The object title prop, pinned first on every object type (see
# api.NAME_PROP_KEY). Tags derive the owner's display name from it.
NAME_PROP_KEY = "name"


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


# --- function views (ADR-0007) ---


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
        inst = instances.get(uuid)
        type_uuid = None if inst is None else inst.type_uuid
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
        name = cast(str | None, getattr(wrapper, NAME_PROP_KEY))
        if not name:
            inst = instances.get(uuid)
            name = "" if inst is None else inst.name
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
        inst = instances.get(uuid)
        type_uuid = None if inst is None else inst.type_uuid
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
        name_prop = aliased(TABLE_Props)
        owner_types = aliased(TABLE_Types)
        rows = Database.session.execute(
            sqla.select(
                TABLE_InstanceValues.inst_uuid,  # owner object uuid
                TABLE_Props.key,  # array prop key
                TABLE_Instances.name,  # owner registry name (fallback title)
                TABLE_StringValues.value,  # owner's `name` prop value (display title)
                owner_types.color,  # owner type's color paints the chip
            )
            .select_from(TABLE_ArrayValues)
            .join(TABLE_InstanceValues, TABLE_InstanceValues.uuid == TABLE_ArrayValues.inst_uuid)
            .join(TABLE_Props, TABLE_Props.uuid == TABLE_InstanceValues.prop_uuid)
            .join(TABLE_Types, TABLE_Types.uuid == TABLE_Props.value_type_uuid)
            .join(TABLE_Instances, TABLE_Instances.uuid == TABLE_InstanceValues.inst_uuid)
            .join(owner_types, owner_types.uuid == TABLE_Instances.type_uuid)
            .join(name_prop, name_prop.owner_type_uuid == TABLE_Instances.type_uuid)
            .join(
                TABLE_StringValues,
                sqla.and_(
                    TABLE_StringValues.inst_uuid == TABLE_Instances.uuid,
                    TABLE_StringValues.prop_uuid == name_prop.uuid,
                ),
                isouter=True,
            )
            .where(
                TABLE_ArrayValues.value_uuid == uuid,
                TABLE_Types.name == WType.array_name(type_name),
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
                        sqla.select(TABLE_Instances.uuid).where(
                            TABLE_Instances.uuid.in_([member.uuid for member in members])
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
            ref=ObjectRef(uuid=value.uuid, type_name=instances[value.uuid].type_name)
        )
