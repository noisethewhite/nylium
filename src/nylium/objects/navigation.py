"""Cross-table navigation and query helpers that are NOT uuid-centric.

The uuid-centric half moved onto the typed identifiers in ``nylium.uuid``
(``TypeUUID.effective_props``, ``TraitUUID.props``, ``PropUUID.purge_values``,
``ObjectUUID.backlink_refs``, …). What remains here takes a Row, a name
string, or a multi-item editor draft and crosses tables one-way so the
``objects`` package stays a DAG.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.Row import mapper
from nylium.data.rows import EnumOption, Instance, NumericValue, Prop, StringValue, Type, UnitPart
from nylium.data.tables import trait_decor, traits, types


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


# --- instance reverse projection ---


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
