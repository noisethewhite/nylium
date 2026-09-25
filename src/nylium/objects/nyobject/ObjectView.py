"""ObjectView — the full instance snapshot: every prop rendered as a
typed PropValue, plus the ADR-0005 reverse tag projection."""
from __future__ import annotations

from dataclasses import field
from decimal import Decimal
from typing import Self, cast
from uuid import UUID

from pydantic.dataclasses import dataclass

from nylium.database import Database
from nylium.data.tables import Instances, instances
from nylium.uuid import ObjectUUID, PropUUID, TypeUUID
from nylium.objects.nyobject.NyObject import NyObject
from nylium.objects.NyType import NyType
from nylium.objects.NyObjectShape import NyObjectShape
from nylium.objects.NyTypeMeta import StoredValue
from nylium.objects.MonthDay import MonthDay
from nylium.objects.MonthDayTime import MonthDayTime
from nylium.objects.Quantity import Quantity
from nylium.objects.NyEnum import NyEnum
from nylium.objects.NyFile import NyFile
from nylium.objects.nyformula import Formula
from nylium.objects.nyfunction.NyFunction import NyFunction
from nylium.objects.NyProp import NyProp
from nylium.objects.NyInteger import NyInteger
from nylium.objects.NyScalar import NyScalar
from nylium.objects.NyScalar import ScalarPayload
from nylium.objects.nyobject.TagView import TagView
from nylium.objects.nyobject.ArrayValue import ArrayValue
from nylium.objects.nyobject.EmbeddedValue import EmbeddedValue
from nylium.objects.nyobject.ObjectRef import ObjectRef
from nylium.objects.nyobject.RefValue import RefValue
from nylium.objects.nyobject.ScalarValue import ScalarValue
from nylium.objects.nyobject.values import PropValue
from nylium.data.tables import InstanceFunctionLinks
from nylium.Constants import Constants


def _sibling_cell(value: StoredValue) -> Decimal | Quantity | str | None:
    """Normalize a sibling prop's stored value for formula folding: plain
    ints/Decimals become Decimal, a Quantity is kept (unit promotion needs
    its part name), a str passes through (an IF cond compares it), and
    everything else folds to unset (→ 0 in evaluation)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, Decimal)):
        return Decimal(value)
    if isinstance(value, Quantity):
        return value
    if isinstance(value, str):
        return value
    return None


def _comparable(value: object) -> object:
    """ADR-0025: reduce a stored bound to its comparable scalar — a Quantity
    compares on its canonical magnitude, everything else passes through."""
    if isinstance(value, Quantity):
        return value.value
    return value


@dataclass(config=Constants.Pydantic.CONFIG)
class ObjectView:
    """Snapshot of one instance: every prop rendered as a typed
    ScalarValue / RefValue / ArrayValue — no Any escapes. `tags` is the
    ADR-0005 reverse projection of the arrays that contain this object.
    `backlinks` is the ADR-0020 reverse projection of every link that
    points at this object — direct link props and array membership."""

    uuid: UUID
    type_name: str
    props: dict[str, PropValue]
    tags: list[TagView] = field(default_factory=list)
    backlinks: list[ObjectRef] = field(default_factory=list)
    # ADR-0029: instance-level function bindings — prop_key -> function_uuid.
    # The frontend uses this to mark computed/read-only props instead of the
    # removed type-level props.function_uuid.
    function_bindings: dict[str, UUID] = field(default_factory=dict)

    @classmethod
    @Database.use_same_session
    def from_uuid(cls, uuid: UUID) -> Self | None:
        inst = instances.get(uuid)
        type_uuid = None if inst is None else inst.type_uuid
        if type_uuid is None:
            return None
        owner = NyType.by_uuid(TypeUUID.of(type_uuid))
        if owner is None:
            raise RuntimeError(f"instance {uuid} has dangling type")
        wrapper = NyObject.wrap(uuid)
        # ADR-0029: function bindings are instance-level — load them once
        # and map prop_uuid -> function_uuid to avoid an N+1 per prop.

        bound = dict(InstanceFunctionLinks.function_links_of_instance(uuid))
        effective = list(NyProp.effective_for(owner))
        props = {
            prop.key: cls._eval_function(uuid, bound[prop.uuid])
            if prop.uuid in bound
            else cls._eval_formula(wrapper, owner, prop)
            if prop.formula is not None
            else cls._render_collect(wrapper, prop)
            if prop.collect is not None
            else cls._render_prop(
                cast(StoredValue, getattr(wrapper, prop.key)),
                prop.value_spec_name(),
            )
            for prop in effective
        }
        function_bindings = {
            prop.key: bound[prop.uuid]
            for prop in effective
            if prop.uuid in bound
        }
        return cls(
            uuid=uuid,
            type_name=owner.name,
            props=props,
            tags=cls._tags_for(uuid, owner.name),
            backlinks=cls._backlinks_for(uuid),
            function_bindings=function_bindings,
        )

    @classmethod
    @Database.use_same_session
    def _backlinks_for(cls, uuid: UUID) -> list[ObjectRef]:
        """ADR-0020: reverse-projection of incoming links — every owner
        pointing at this object through a link prop or an array. One
        query per direction, no N+1."""
        return [
            ObjectRef(uuid=owner_uuid, type_name=type_name)
            for owner_uuid, type_name in ObjectUUID.of(uuid).backlink_refs()
        ]

    @classmethod
    @Database.use_same_session
    def _tags_for(cls, uuid: UUID, type_name: str) -> list[TagView]:
        """ADR-0005: reverse-projection of array membership. Every
        ``Array<type_name>`` prop whose stored array contains this object
        becomes one tag ``<owner display name> → <prop key>``. One query,
        no N+1."""
        rows = ObjectUUID.of(uuid).array_tag_rows(NyType.array_name(type_name), Constants.Props.NAME_PROP_KEY)
        tags: list[TagView] = []
        for owner_uuid, prop_key, registry_name, display_name, color in rows:
            display_name = display_name or registry_name
            tags.append(
                TagView(
                    owner_uuid=owner_uuid,
                    owner_name=display_name,
                    prop_key=prop_key,
                    name=f"{display_name} {Constants.Embedded.NAME_SEPARATOR} {prop_key}",
                    color=color,
                )
            )
        tags.sort(key=lambda tag: (tag.owner_name, tag.prop_key))
        return tags

    @classmethod
    @Database.use_same_session
    def _eval_function(cls, inst_uuid: UUID, function_uuid: UUID) -> ScalarValue:
        """ADR-0029 read-time evaluation: fold the function's DAG over the
        owner's sibling props. A div-by-zero / missing input renders empty."""
        value = NyFunction.evaluate_for(inst_uuid, function_uuid)
        return ScalarValue(value=value)

    @classmethod
    @Database.use_same_session
    def _eval_formula(cls, wrapper: NyObjectShape, owner: NyType, prop: NyProp) -> ScalarValue:
        """ADR-0005/0022/0023 read-time evaluation: fold the stored formula
        over the live rows of the arrays it references, the owner's sibling
        prop values and (one level down) computed member props. Unset cells
        count as 0; a dangling member keeps its stored row (COUNT sees it,
        the numeric aggregates treat it as 0). A unit result renders as a
        Quantity (value + part); division by zero renders empty."""
        assert prop.formula is not None
        result = cls._evaluate_formula(wrapper, owner, prop.formula)
        if result is None:
            return ScalarValue(value=None)
        if prop.value_type().name == NyInteger.TYPE_NAME:
            return ScalarValue(value=int(cast(Decimal, result)))
        if NyType.unit_param_of(prop.value_type().name) is not None:
            if isinstance(result, Quantity):
                return ScalarValue(value=result.value, unit=result.unit)
            return ScalarValue(value=result)
        if isinstance(result, Quantity):
            return ScalarValue(value=result.value)
        return ScalarValue(value=result)

    @classmethod
    def _evaluate_formula(
        cls, wrapper: NyObjectShape, owner: NyType, formula: str
    ) -> Decimal | Quantity | None:
        """Fold a formula over an owner's array rows and sibling props,
        returning the raw value (None on division by zero). A computed
        member prop of an array element folds one level down (ADR-0023)."""
        refs = Formula.references(formula)
        arrays: dict[str, list[dict[str, Decimal | Quantity | None]]] = {}
        for array_key in {key for key, _ in refs}:
            array_prop = NyProp.effective_by_key(owner, array_key)
            element_type = None
            if array_prop is not None:
                element_type = NyType.by_name(
                    NyType.element_name(array_prop.value_type().name)
                )
            member_schema = (
                {p.key: p for p in NyProp.effective_for(element_type)}
                if element_type is not None
                else {}
            )
            members = (
                [NyObject.wrap(u) for u in cls._collect_uuids(wrapper, array_prop)]
                if array_prop is not None and array_prop.collect is not None
                else cast(list[NyObjectShape] | None, getattr(wrapper, array_key)) or []
            )
            existing: set[UUID] = (
                Instances.existing_uuids([member.uuid for member in members]) if members else set()
            )
            wanted = {member for key, member in refs if key == array_key and member}
            rows: list[dict[str, Decimal | Quantity | None]] = []
            for member in members:
                if member.uuid not in existing:
                    rows.append({})
                    continue
                row: dict[str, Decimal | Quantity | None] = {}
                for key in wanted:
                    row[key] = cls._member_cell(member, element_type, member_schema.get(key))
                rows.append(row)
            arrays[array_key] = rows
        scalars = {
            key: _sibling_cell(cast(StoredValue, getattr(wrapper, key)))
            for key in Formula.sibling_references(formula)
        }
        return Formula.evaluate(formula, arrays, scalars)

    @classmethod
    def _member_cell(
        cls, member: NyObjectShape, element_type: NyType | None, prop: NyProp | None
    ) -> Decimal | Quantity | None:
        """One member cell. A computed member prop folds its own formula
        over the member's siblings (the ADR-0023 chained level); otherwise
        the stored value normalizes via _sibling_cell, keeping a Quantity's
        part so aggregates stay unit-aware."""
        if prop is None:
            return None
        if prop.formula is not None:
            if element_type is None:
                return None
            return cls._evaluate_formula(member, element_type, prop.formula)
        value = _sibling_cell(cast(StoredValue, getattr(member, prop.key)))
        return None if isinstance(value, str) else value

    @classmethod
    @Database.use_same_session
    def _collect_uuids(cls, wrapper: NyObjectShape, prop: NyProp) -> list[ObjectUUID]:
        """ADR-0025: the derived member uuids of a collect prop — one reverse
        range query over the target type's member prop, bounded by the owner's
        from/to siblings. Missing bounds / dangling member yield an empty set."""
        assert prop.collect is not None
        element_type = NyType.by_name(NyType.element_name(prop.value_type().name))
        member_prop = (
            NyProp.effective_by_key(element_type, prop.collect)
            if element_type is not None
            else None
        )
        lo = _comparable(cast(StoredValue, getattr(wrapper, "from")))
        hi = _comparable(cast(StoredValue, getattr(wrapper, "to")))
        if member_prop is None or lo is None or hi is None:
            return []
        return PropUUID.of(member_prop.uuid).collect_range(member_prop.value_spec_name(), lo, hi)

    @classmethod
    @Database.use_same_session
    def _render_collect(cls, wrapper: NyObjectShape, prop: NyProp) -> ArrayValue:
        """ADR-0025: render a collect prop as an array of refs to the derived
        members (same shape as a stored Array<T> of standalone objects)."""
        element_name = NyType.element_name(prop.value_type().name)
        return ArrayValue(
            items=[
                RefValue(ref=ObjectRef(uuid=u, type_name=element_name))
                for u in cls._collect_uuids(wrapper, prop)
            ]
        )

    @classmethod
    @Database.use_same_session
    def _render_prop(cls, value: StoredValue, type_name: str) -> PropValue:
        """The declared prop type disambiguates None: an unset scalar,
        an unset link and an unset array are three different views."""
        if NyScalar.by_type_name(type_name) is not None:
            # year-less calendar values cross the wire as their stamps
            if isinstance(value, (MonthDay, MonthDayTime)):
                return ScalarValue(value=str(value))
            return ScalarValue(value=cast(ScalarPayload | None, value))
        if NyType.unit_param_of(type_name) is not None:
            # Quantity: canonical magnitude re-scaled to the entered part,
            # rendered with the part name attached
            if value is None:
                return ScalarValue(value=None)
            if not isinstance(value, Quantity):
                raise TypeError(f"unit prop rendered a {type(value).__name__}")
            return ScalarValue(value=value.value, unit=value.unit)
        if NyEnum.is_enum(type_name):
            return ScalarValue(value=cast(str | None, value))
        if NyFile.is_file_type(type_name):
            # ADR-0008: a file-typed prop renders as a ref to the files row
            # — the uuid is the pointer, the type name is the declared one
            if value is None:
                return RefValue(ref=None)
            if not isinstance(value, UUID):
                raise TypeError(f"file prop rendered a {type(value).__name__}")
            return RefValue(ref=ObjectRef(uuid=value, type_name=type_name))
        if NyType.is_array_name(type_name):
            element_name = NyType.element_name(type_name)
            if value is None:
                return ArrayValue(items=None)
            if not isinstance(value, list):
                raise TypeError(f"array prop rendered a {type(value).__name__}")
            return ArrayValue(
                items=[cls._render_prop(item, element_name) for item in value]
            )
        owner = NyType.by_name(type_name)
        if owner is not None and owner.is_embedded:
            # composition child: rendered as the full nested props view,
            # so the editor can inline its fields without a second fetch
            if value is None:
                return EmbeddedValue(uuid=None, type_name=type_name, props={})
            if not isinstance(value, NyObject):
                raise TypeError(f"embedded prop rendered a {type(value).__name__}")
            child = ObjectView.from_uuid(value.uuid)
            if child is None:
                raise RuntimeError(f"embedded child {value.uuid} vanished")
            return EmbeddedValue(uuid=child.uuid, type_name=type_name, props=child.props)
        if value is None:
            return RefValue(ref=None)
        if not isinstance(value, NyObject):
            raise TypeError(f"link prop rendered a {type(value).__name__}")
        return RefValue(
            ref=ObjectRef(uuid=value.uuid, type_name=TypeUUID.of(instances[value.uuid].type_uuid).name_of())
        )
