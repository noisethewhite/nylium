"""Cross-table navigation and query helpers (ADR-0033).

The mapped-dataclass ``Row`` carries only its own columns — no navigation
properties or cross-table store methods that would ``import`` a sibling
table (pyright tracks function-level imports too, so a ``Type.props`` +
``Prop.value_type`` pair would re-introduce the import cycle ADR-0033
removes). The effective-schema, decor, reverse-projection and cross-table
sync logic lives here instead, where every table is imported one-way and
the ``objects`` package stays a DAG.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Protocol, cast
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Mapped, aliased

from nylium.database import Database
from nylium.database.Row import mapper
from nylium.database.Table import Row
from nylium.objects.scalar_type_names import DATE, DATETIME, INTEGER
from nylium.data.tables import trait_decor
from nylium.data.tables import type_decor
from nylium.data.rows import TypeDecor
from nylium.data.rows import EnumOption
from nylium.data.rows import Instance
from nylium.data.rows import Prop
from nylium.data.rows import Type
from nylium.data.rows import UnitPart
from nylium.data.tables import enum_options
from nylium.data.tables import props
from nylium.data.tables import traits
from nylium.data.tables import type_traits
from nylium.data.tables import types
from nylium.data.tables import unit_parts
from nylium.data.rows import ArrayValue
from nylium.data.rows import BooleanValue
from nylium.data.rows import DateValue
from nylium.data.rows import DatetimeValue
from nylium.data.rows import InstanceValue
from nylium.data.rows import IntegerValue
from nylium.data.rows import MonthDayTimeValue
from nylium.data.rows import MonthDayValue
from nylium.data.rows import NumericValue
from nylium.data.rows import StringValue
from nylium.data.rows import TimeValue

# --- schema navigation (was Row properties) ---


def effective_props(type_uuid: UUID) -> list[Prop]:
    """The *effective* schema (ADR-0013): own props, then each attached
    trait's props in attach order."""
    result = sorted(props.where(owner_type_uuid=type_uuid), key=lambda p: p.position)
    for trait_uuid in type_traits.attached_trait_uuids(type_uuid):
        result.extend(
            sorted(props.where(owner_trait_uuid=trait_uuid), key=lambda p: p.position)
        )
    return result


def prop_value_type_name(prop: Prop) -> str:
    """The wire-facing value spec: the concrete type's name, or
    ``Any<TraitName>`` for a trait-bound prop (ADR-0013)."""
    if prop.value_trait_uuid is not None:
        t = traits.get(prop.value_trait_uuid)
        if t is None:
            raise KeyError(f"Trait with UUID {prop.value_trait_uuid} does not exist")
        return f"Any<{t.name}>"
    if prop.value_type_uuid is None:
        raise KeyError(f"Prop {prop.key!r} has no value typing")
    t = types.get(prop.value_type_uuid)
    if t is None:
        raise KeyError(f"Type with UUID {prop.value_type_uuid} does not exist")
    return t.name


def prop_owner_trait(prop: Prop) -> tuple[str, str] | None:
    """``(name, color)`` of the owning trait, None for a type-owned prop."""
    if prop.owner_trait_uuid is None:
        return None
    t = traits.get(prop.owner_trait_uuid)
    if t is None:
        raise KeyError(f"Trait with UUID {prop.owner_trait_uuid} does not exist")
    return t.name, trait_decor[t.uuid].color


def type_plural_name(type_uuid: UUID) -> str:
    return type_decor[type_uuid].plural_name


def type_icon(type_uuid: UUID) -> str:
    return type_decor[type_uuid].icon


def type_color(type_uuid: UUID) -> str:
    return type_decor[type_uuid].color


def type_trait_names(type_uuid: UUID) -> list[str]:
    """Names of traits attached to this type, in attach order."""
    result: list[str] = []
    for link in sorted(
        type_traits.where(type_uuid=type_uuid), key=lambda link: link.position
    ):
        trait = traits.get(link.trait_uuid)
        if trait is not None:
            result.append(trait.name)
    return result


def type_enum_options(type_uuid: UUID) -> list[EnumOption]:
    return sorted(enum_options.where(type_uuid=type_uuid), key=lambda o: o.position)


def type_unit_parts(type_uuid: UUID) -> list[UnitPart]:
    return sorted(unit_parts.where(type_uuid=type_uuid), key=lambda p: p.position)


def trait_color(trait_uuid: UUID) -> str:
    return trait_decor[trait_uuid].color


def trait_props(trait_uuid: UUID) -> list[Prop]:
    return sorted(props.where(owner_trait_uuid=trait_uuid), key=lambda p: p.position)


def trait_attached_names(trait_uuid: UUID) -> list[str]:
    """Names of types this trait is attached to, in attach order."""
    result: list[str] = []
    for link in sorted(
        type_traits.where(trait_uuid=trait_uuid), key=lambda link: link.position
    ):
        owner = types.get(link.type_uuid)
        if owner is not None:
            result.append(owner.name)
    return result


def type_name_of(type_uuid: UUID) -> str:
    """The type's name, or ``<dangling>`` if the type row is gone."""
    t = types.get(type_uuid)
    return "<dangling>" if t is None else t.name


# --- prop value purge (was Props.purge_values*) ---


class _PropKeyedValues(Protocol):
    inst_uuid: Mapped[UUID]
    prop_uuid: Mapped[UUID]


# Tables keyed by prop_uuid — a retype wipes the old values from all of
# them so the new type starts clean (Null) on every instance.
_PROP_KEYED_VALUE_TABLES: tuple[type[_PropKeyedValues], ...] = (
    StringValue,
    IntegerValue,
    NumericValue,
    BooleanValue,
    DatetimeValue,
    DateValue,
    TimeValue,
    MonthDayValue,
    MonthDayTimeValue,
    InstanceValue,
)


@Database.use_same_session
def purge_prop_values(prop_uuid: UUID) -> None:
    """Wipe every stored value of one prop across all value tables."""
    for table in _PROP_KEYED_VALUE_TABLES:
        tc = mapper(table).columns
        _ = Database.execute(sqla.delete(table).where(tc.prop_uuid == prop_uuid))
    Database.flush()


@Database.use_same_session
def purge_prop_values_for_instances(prop_uuid: UUID, inst_uuids: list[UUID]) -> None:
    """ADR-0013 detach: wipe this prop's values, but only on the given
    instances (the trait's other types keep theirs)."""
    if not inst_uuids:
        return
    for table in _PROP_KEYED_VALUE_TABLES:
        tc = mapper(table).columns
        _ = Database.execute(
            sqla.delete(table).where(
                tc.prop_uuid == prop_uuid,
                tc.inst_uuid.in_(inst_uuids),
            )
        )
    Database.flush()


# --- enum options (was EnumOptions.count_usage/sync) ---


@Database.use_same_session
def _enum_option_usage(type_uuid: UUID, value: str) -> int:
    sv_c = mapper(StringValue).columns
    p_c = mapper(Prop).columns
    return int(
        Database.scalar(
            sqla.select(sqla.func.count())
            .select_from(StringValue)
            .join(Prop, sv_c.prop_uuid == p_c.uuid)
            .where(p_c.value_type_uuid == type_uuid, sv_c.value == value)
        )
        or 0
    )


@Database.commit_after_this
def sync_enum_options(type_uuid: UUID, items: list[tuple[UUID | None, str]]) -> None:
    """Apply the enum editor's full option draft: matching uuid renames
    (propagating to stored values), None creates, absent options are
    deleted unless still in use."""
    c = mapper(EnumOption).columns
    existing = {
        row.uuid: row
        for row in Database.scalars(
            sqla.select(EnumOption).where(c.type_uuid == type_uuid)
        )
    }
    kept = {uuid for uuid, _ in items if uuid is not None}
    for stale_uuid, stale_row in existing.items():
        if stale_uuid in kept:
            continue
        usage = _enum_option_usage(type_uuid, stale_row.value)
        if usage:
            raise ValueError(
                f"option {stale_row.value!r} is still used by {usage} values"
            )
        Database.delete(stale_row)
    Database.flush()
    for position, (option_uuid, value) in enumerate(items):
        if option_uuid is None or option_uuid not in existing:
            Database.add(
                EnumOption(uuid=uuid4(), type_uuid=type_uuid, value=value, position=position)
            )
            continue
        row = existing[option_uuid]
        if row.value != value:
            sv_c = mapper(StringValue).columns
            p_c = mapper(Prop).columns
            _ = Database.execute(
                sqla.update(StringValue)
                .where(
                    sv_c.value == row.value,
                    sv_c.prop_uuid.in_(
                        sqla.select(p_c.uuid).where(p_c.value_type_uuid == type_uuid)
                    ),
                )
                .values(value=value)
            )
            row.value = value
        row.position = position
    Database.flush()


# --- unit parts (was UnitParts._parameterized_uuid/usage_count/sync) ---


@Database.use_same_session
def parameterized_numeric_uuid(unit_type_name: str) -> UUID | None:
    """The uuid of the ``Numeric<Unit>`` parameterized type row."""
    t_c = mapper(Type).columns
    return Database.scalar(
        sqla.select(t_c.uuid).where(t_c.name == f"Numeric<{unit_type_name}>")
    )


@Database.use_same_session
def unit_part_usage(unit_type_name: str, part_name: str | None = None) -> int:
    """How many stored values reference this unit (optionally one part)."""
    parameterized_uuid = parameterized_numeric_uuid(unit_type_name)
    if parameterized_uuid is None:
        return 0
    p_c = mapper(Prop).columns
    nv_c = mapper(NumericValue).columns
    conditions: list[sqla.ColumnElement[bool]] = [
        p_c.value_type_uuid == parameterized_uuid,
        nv_c.prop_uuid == p_c.uuid,
    ]
    if part_name is not None:
        conditions.append(nv_c.unit == part_name)
    return int(
        Database.scalar(
            sqla.select(sqla.func.count()).select_from(NumericValue).where(*conditions)
        )
        or 0
    )


@Database.commit_after_this
def sync_unit_parts(
    type_uuid: UUID,
    unit_type_name: str,
    items: list[tuple[UUID | None, str, Decimal, Decimal, bool]],
) -> None:
    """Apply the unit editor's full part draft: matching uuid edits in
    place (a rename propagates to stored values), None creates, absent
    parts are deleted unless still in use."""
    c = mapper(UnitPart).columns
    existing = sorted(
        Database.scalars(sqla.select(UnitPart).where(c.type_uuid == type_uuid)),
        key=lambda p: p.position,
    )
    by_uuid = {part.uuid: part for part in existing}
    seen: set[UUID] = set()
    for position, (uuid, name, multiplier, offset, is_base) in enumerate(items):
        part = by_uuid.get(uuid) if uuid is not None else None
        if part is None:
            row = UnitPart(
                uuid=uuid4(),
                type_uuid=type_uuid,
                name=name,
                multiplier=multiplier,
                offset=offset,
                is_base=is_base,
                position=position,
            )
            Database.add(row)
            Database.flush()
            part = row
        else:
            if part.name != name:
                parameterized_uuid = parameterized_numeric_uuid(unit_type_name)
                if parameterized_uuid is not None:
                    p_c = mapper(Prop).columns
                    nv_c = mapper(NumericValue).columns
                    _ = Database.execute(
                        sqla.update(NumericValue)
                        .where(
                            nv_c.prop_uuid.in_(
                                sqla.select(p_c.uuid).where(
                                    p_c.value_type_uuid == parameterized_uuid,
                                )
                            ),
                            nv_c.unit == part.name,
                        )
                        .values(unit=name)
                    )
                part.name = name
            part.multiplier = multiplier
            part.offset = offset
            part.is_base = is_base
            part.position = position
        seen.add(part.uuid)
    for part in existing:
        if part.uuid in seen:
            continue
        usage = unit_part_usage(unit_type_name, part.name)
        if usage:
            raise ValueError(f"unit part {part.name!r} still has {usage} values")
        _ = Database.execute(sqla.delete(UnitPart).where(c.uuid == part.uuid))
    Database.flush()


# --- instance / link / array reverse projections (was store methods) ---


@Database.use_same_session
def instance_uuids_of_kind(kind: str) -> list[UUID]:
    """Every instance uuid whose type has the given kind."""
    i_c = mapper(Instance).columns
    t_c = mapper(Type).columns
    return list(
        Database.scalars(
            sqla.select(i_c.uuid)
            .join(Type, t_c.uuid == i_c.type_uuid)
            .where(t_c.kind == kind)
        ).all()
    )


@Database.use_same_session
def array_link_uuids_of(owner_inst_uuid: UUID) -> list[UUID]:
    """Uuids of array-instance links held by the given owner."""
    iv_c = mapper(InstanceValue).columns
    p_c = mapper(Prop).columns
    t_c = mapper(Type).columns
    stmt = (
        sqla.select(iv_c.uuid)
        .join(Prop, iv_c.prop_uuid == p_c.uuid)
        .join(Type, p_c.value_type_uuid == t_c.uuid)
        .where(
            iv_c.inst_uuid == owner_inst_uuid,
            # mirrors NyType.ARRAY_TYPE_PREFIX (objects layer imports tables,
            # so the constant cannot flow the other way)
            t_c.name.like("Array<%"),
        )
    )
    return list(Database.scalars(stmt).all())


@Database.use_same_session
def backlink_refs(target_uuid: UUID) -> list[tuple[UUID, str]]:
    """(owner uuid, owner type name) for every instance that points at
    ``target_uuid`` — directly through a link prop or through membership
    in one of its arrays. Owners deduplicated, direct links first."""
    iv_c = mapper(InstanceValue).columns
    i_c = mapper(Instance).columns
    av_c = mapper(ArrayValue).columns

    direct_types = aliased(Type)
    direct = Database.execute(
        sqla.select(iv_c.inst_uuid, direct_types.name)
        .join(Instance, iv_c.inst_uuid == i_c.uuid)
        .join(direct_types, i_c.type_uuid == direct_types.uuid)
        .where(iv_c.uuid == target_uuid)
    ).all()

    box_link = aliased(InstanceValue)
    array_types = aliased(Type)
    via_arrays = Database.execute(
        sqla.select(box_link.inst_uuid, array_types.name)
        .select_from(ArrayValue)
        .join(box_link, av_c.inst_uuid == box_link.uuid)
        .join(Instance, box_link.inst_uuid == i_c.uuid)
        .join(array_types, i_c.type_uuid == array_types.uuid)
        .where(av_c.value_uuid == target_uuid)
    ).all()

    seen: set[UUID] = set()
    refs: list[tuple[UUID, str]] = []
    for r in [*direct, *via_arrays]:
        owner_uuid = cast(UUID, r[0])
        if owner_uuid in seen:
            continue
        seen.add(owner_uuid)
        refs.append((owner_uuid, cast(str, r[1])))
    # deterministic wire order: SQL row order is an implementation detail
    return sorted(refs, key=lambda item: (item[1], str(item[0])))


@Database.use_same_session
def array_tag_rows(
    element_uuid: UUID, array_type_name: str, name_prop_key: str
) -> list[tuple[UUID, str, str, str | None, str]]:
    """ADR-0005 reverse projection: every array that holds ``element_uuid``
    as a member of an ``Array<array_type_name>`` prop, with enough info to
    paint a tag chip — (owner uuid, prop key, registry name, display name,
    owner type color). One query, no N+1."""
    name_prop = aliased(Prop)
    owner_types = aliased(Type)
    owner_decor = aliased(TypeDecor)
    av_c = mapper(ArrayValue).columns
    iv_c = mapper(InstanceValue).columns
    p_c = mapper(Prop).columns
    i_c = mapper(Instance).columns
    s_c = mapper(StringValue).columns
    t_c = mapper(Type).columns
    rows = Database.execute(
        sqla.select(
            iv_c.inst_uuid,
            p_c.key,
            i_c.name,
            s_c.value,
            owner_decor.color,
        )
        .select_from(ArrayValue)
        .join(InstanceValue, iv_c.uuid == av_c.inst_uuid)
        .join(Prop, p_c.uuid == iv_c.prop_uuid)
        .join(Type, t_c.uuid == p_c.value_type_uuid)
        .join(Instance, i_c.uuid == iv_c.inst_uuid)
        .join(owner_types, owner_types.uuid == i_c.type_uuid)
        .join(owner_decor, owner_decor.uuid == owner_types.uuid)
        .join(name_prop, name_prop.owner_type_uuid == i_c.type_uuid)
        .join(
            StringValue,
            sqla.and_(
                s_c.inst_uuid == i_c.uuid,
                s_c.prop_uuid == name_prop.uuid,
            ),
            isouter=True,
        )
        .where(
            av_c.value_uuid == element_uuid,
            t_c.name == array_type_name,
            name_prop.key == name_prop_key,
        )
        .distinct()
    ).all()
    return [
        (
            cast(UUID, r[0]),
            cast(str, r[1]),
            cast(str, r[2]),
            cast("str | None", r[3]),
            cast(str, r[4]),
        )
        for r in rows
    ]


@Database.use_same_session
def collect_range(
    prop_uuid: UUID, spec_name: str, lo: object, hi: object
) -> list[UUID]:
    """Every instance whose `prop_uuid` value falls within [lo, hi] inclusive.

    `spec_name` is the member prop's value spec (ordered scalar); it picks
    the matching value table."""
    if spec_name == INTEGER:
        table: type[Row] = IntegerValue
    elif spec_name == DATE:
        table = DateValue
    elif spec_name == DATETIME:
        table = DatetimeValue
    else:
        # Numeric and Numeric<Unit> both store their magnitude in numeric_values
        table = NumericValue
    c = mapper(table).columns
    return list(
        Database.scalars(
            sqla.select(c.inst_uuid).where(
                c.prop_uuid == prop_uuid,
                c.value >= lo,
                c.value <= hi,
            )
        ).all()
    )
