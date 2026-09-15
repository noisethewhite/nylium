"""ObjectView — the full instance snapshot: every prop rendered as a
typed PropValue, plus the ADR-0005 reverse tag projection."""
from __future__ import annotations

from dataclasses import field
from decimal import Decimal
from typing import Self, cast
from uuid import UUID

from pydantic.dataclasses import dataclass

from nylium.database import databasemethod
from nylium.tables import instances
from nylium.tables.objects.instances import existing_uuids
from nylium.tables.values.array_values import array_tag_rows
from nylium.tables.values.backlinks import backlink_refs
from nylium.objects import WObject, WType
from nylium.objects.wtypemeta import StoredValue, WObjectShape
from nylium.objects.monthday import MonthDay, MonthDayTime
from nylium.objects.quantity import Quantity
from nylium.objects.wembedded import EMBEDDED_NAME_SEPARATOR
from nylium.objects.wenum import WEnum
from nylium.objects.wfile import WFile
from nylium.objects.wformula import Formula
from nylium.objects.wfunction import WFunction
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import ScalarPayload, WInteger, WScalar
from nylium.api.display.tags import TagView
from nylium.api.display.values import (
    CONFIG,
    NAME_PROP_KEY,
    ArrayValue,
    EmbeddedValue,
    ObjectRef,
    PropValue,
    RefValue,
    ScalarValue,
)


def _sibling_cell(value: StoredValue) -> Decimal | Quantity | None:
    """Normalize a sibling prop's stored value for formula folding: plain
    ints/Decimals become Decimal, a Quantity is kept (unit promotion needs
    its part name), everything else folds to unset (→ 0 in evaluation)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, Decimal)):
        return Decimal(value)
    if isinstance(value, Quantity):
        return value
    return None


@dataclass(config=CONFIG)
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
                prop.value_spec_name(),
            )
            for prop in WProp.effective_for(owner)
        }
        return cls(
            uuid=uuid,
            type_name=owner.name,
            props=props,
            tags=cls._tags_for(uuid, owner.name),
            backlinks=cls._backlinks_for(uuid),
        )

    @classmethod
    @databasemethod(commit=False)
    def _backlinks_for(cls, uuid: UUID) -> list[ObjectRef]:
        """ADR-0020: reverse-projection of incoming links — every owner
        pointing at this object through a link prop or an array. One
        query per direction, no N+1."""
        return [
            ObjectRef(uuid=owner_uuid, type_name=type_name)
            for owner_uuid, type_name in backlink_refs(uuid)
        ]

    @classmethod
    @databasemethod(commit=False)
    def _tags_for(cls, uuid: UUID, type_name: str) -> list[TagView]:
        """ADR-0005: reverse-projection of array membership. Every
        ``Array<type_name>`` prop whose stored array contains this object
        becomes one tag ``<owner display name> → <prop key>``. One query,
        no N+1."""
        rows = array_tag_rows(uuid, WType.array_name(type_name), NAME_PROP_KEY)
        tags: list[TagView] = []
        for owner_uuid, prop_key, registry_name, display_name, color in rows:
            display_name = display_name or registry_name
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
    def _eval_function(cls, prop: WProp) -> ScalarValue:
        """ADR-0007 read-time evaluation: fold the function's DAG over its
        current input object. A div-by-zero / missing input renders empty."""
        assert prop.function_uuid is not None
        value = WFunction.evaluate_for(prop.function_uuid)
        return ScalarValue(value=value)

    @classmethod
    @databasemethod(commit=False)
    def _eval_formula(cls, wrapper: WObjectShape, prop: WProp) -> ScalarValue:
        """ADR-0005/0022 read-time evaluation: fold the stored formula over
        the live rows of the arrays it references and the owner's sibling
        prop values. Unset cells count as 0; a dangling member keeps its
        stored row (COUNT sees it, the numeric aggregates treat it as 0).
        A unit result renders as a Quantity (value + part); division by
        zero renders empty."""
        assert prop.formula is not None
        refs = Formula.references(prop.formula)
        arrays: dict[str, list[dict[str, Decimal | None]]] = {}
        for array_key in {key for key, _ in refs}:
            members = cast(list[WObjectShape] | None, getattr(wrapper, array_key)) or []
            existing: set[UUID] = (
                existing_uuids([member.uuid for member in members])
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
        scalars = {
            key: _sibling_cell(cast(StoredValue, getattr(wrapper, key)))
            for key in Formula.sibling_references(prop.formula)
        }
        result = Formula.evaluate(prop.formula, arrays, scalars)
        if result is None:
            return ScalarValue(value=None)
        if prop.value_type().name == WInteger.TYPE_NAME:
            return ScalarValue(value=int(cast(Decimal, result)))
        if WType.unit_param_of(prop.value_type().name) is not None:
            if isinstance(result, Quantity):
                return ScalarValue(value=result.value, unit=result.unit)
            return ScalarValue(value=result)
        if isinstance(result, Quantity):
            return ScalarValue(value=result.value)
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
