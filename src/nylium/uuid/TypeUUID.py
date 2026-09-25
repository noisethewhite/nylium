"""TypeUUID — typed identifier for a ``Type`` row (``types``)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sqla
from pydantic_core import core_schema

from nylium.database import Database
from nylium.database.Row import get_mapper
from nylium.database.Table import Row
from nylium.data.rows import EnumOption, NumericValue, Prop, StringValue, Type, UnitPart
from nylium.data.tables import (
    enum_options,
    props,
    traits,
    type_style,
    type_traits,
    types,
    unit_parts,
)


class TypeUUID(UUID):
    """A ``types`` uuid carrying its own table lookup and schema navigation."""

    @classmethod
    def of(cls, value: UUID) -> "TypeUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> Type | None:
        """The ``Type`` row this uuid points at, or ``None`` if it is gone."""
        return types.get(self)

    def effective_props(self) -> list[Prop]:
        """The effective schema (ADR-0013): own props, then each attached
        trait's props in attach order."""
        result = sorted(props.where(owner_type_uuid=self), key=lambda p: p.position)
        for trait_uuid in type_traits.attached_trait_uuids(self):
            result.extend(
                sorted(props.where(owner_trait_uuid=trait_uuid), key=lambda p: p.position)
            )
        return result

    def plural_name(self) -> str:
        return type_style[self].plural_name

    def icon(self) -> str:
        return type_style[self].icon

    def color(self) -> str:
        return type_style[self].color

    def trait_names(self) -> list[str]:
        """Names of traits attached to this type, in attach order."""
        result: list[str] = []
        for link in sorted(type_traits.where(type_uuid=self), key=lambda link: link.position):
            trait = traits.get(link.trait_uuid)
            if trait is not None:
                result.append(trait.name)
        return result

    def enum_options(self) -> list[EnumOption]:
        return sorted(enum_options.where(type_uuid=self), key=lambda o: o.position)

    def unit_parts(self) -> list[UnitPart]:
        return sorted(unit_parts.where(type_uuid=self), key=lambda p: p.position)

    def name_of(self) -> str:
        """The type's name, or ``<dangling>`` if the type row is gone."""
        t = types.get(self)
        return "<dangling>" if t is None else t.name

    # --- shared draft helpers (enum + unit share the same shape) ---

    @classmethod
    @Database.use_same_session
    def _usage_count(
        cls,
        value_table: type[Row],
        type_uuid: UUID,
        *,
        condition: sqla.ColumnElement[bool] | None = None,
    ) -> int:
        """How many stored values reference a type (optionally one value)."""
        v_c = get_mapper(value_table).columns
        p_c = get_mapper(Prop).columns
        stmt = (
            sqla.select(sqla.func.count())
            .select_from(value_table)
            .join(Prop, v_c.prop_uuid == p_c.uuid)
            .where(p_c.value_type_uuid == type_uuid)
        )
        if condition is not None:
            stmt = stmt.where(condition)
        return int(Database.scalar(stmt) or 0)

    @classmethod
    @Database.use_same_session
    def _rename_propagate(
        cls,
        value_table: type[Row],
        type_uuid: UUID,
        value_column: sqla.Column[object],
        old_value: object,
        new_value: object,
    ) -> None:
        """Rewrite a stored value column across the type's props (rename)."""
        v_c = get_mapper(value_table).columns
        p_c = get_mapper(Prop).columns
        _ = Database.execute(
            sqla.update(value_table)
            .where(
                value_column == old_value,
                v_c.prop_uuid.in_(sqla.select(p_c.uuid).where(p_c.value_type_uuid == type_uuid)),
            )
            .values({value_column: new_value})
        )

    # --- enum options ---

    @Database.use_same_session
    def _enum_option_usage(self, value: str) -> int:
        return self._usage_count(
            StringValue, self, condition=get_mapper(StringValue).columns.value == value
        )

    @Database.commit_after_this
    def sync_enum_options(self, items: list[tuple[UUID | None, str]]) -> None:
        """Apply the enum editor's full option draft: matching uuid renames
        (propagating to stored values), None creates, absent options are
        deleted unless still in use."""
        c = get_mapper(EnumOption).columns
        existing = {
            row.uuid: row
            for row in Database.scalars(sqla.select(EnumOption).where(c.type_uuid == self))
        }
        kept = {uuid for uuid, _ in items if uuid is not None}
        for stale_uuid, stale_row in existing.items():
            if stale_uuid in kept:
                continue
            usage = self._enum_option_usage(stale_row.value)
            if usage:
                raise ValueError(f"option {stale_row.value!r} is still used by {usage} values")
            Database.delete(stale_row)
        Database.flush()
        for position, (option_uuid, value) in enumerate(items):
            if option_uuid is None or option_uuid not in existing:
                Database.add(
                    EnumOption(uuid=uuid4(), type_uuid=self, value=value, position=position)
                )
                continue
            row = existing[option_uuid]
            if row.value != value:
                self._rename_propagate(
                    StringValue, self, get_mapper(StringValue).columns.value, row.value, value
                )
                row.value = value
            row.position = position
        Database.flush()

    # --- unit parts ---

    @classmethod
    @Database.use_same_session
    def parameterized_numeric(cls, unit_type_name: str) -> "TypeUUID | None":
        """The uuid of the ``Numeric<Unit>`` parameterized type row."""
        t_c = get_mapper(Type).columns
        raw: UUID | None = Database.scalar(
            sqla.select(t_c.uuid).where(t_c.name == f"Numeric<{unit_type_name}>")
        )
        return None if raw is None else cls.of(raw)

    @classmethod
    @Database.use_same_session
    def unit_part_usage(cls, unit_type_name: str, part_name: str | None = None) -> int:
        """How many stored values reference this unit (optionally one part)."""
        parameterized = cls.parameterized_numeric(unit_type_name)
        if parameterized is None:
            return 0
        condition = None if part_name is None else get_mapper(NumericValue).columns.unit == part_name
        return cls._usage_count(NumericValue, parameterized, condition=condition)

    @Database.commit_after_this
    def sync_unit_parts(
        self,
        unit_type_name: str,
        items: list[tuple[UUID | None, str, Decimal, Decimal, bool]],
    ) -> None:
        """Apply the unit editor's full part draft: matching uuid edits in
        place (a rename propagates to stored values), None creates, absent
        parts are deleted unless still in use."""
        c = get_mapper(UnitPart).columns
        existing = sorted(
            Database.scalars(sqla.select(UnitPart).where(c.type_uuid == self)),
            key=lambda p: p.position,
        )
        by_uuid = {part.uuid: part for part in existing}
        seen: set[UUID] = set()
        for position, (uuid, name, multiplier, offset, is_base) in enumerate(items):
            part = by_uuid.get(uuid) if uuid is not None else None
            if part is None:
                row = UnitPart(
                    uuid=uuid4(),
                    type_uuid=self,
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
                    parameterized = self.parameterized_numeric(unit_type_name)
                    if parameterized is not None:
                        self._rename_propagate(
                            NumericValue, parameterized, get_mapper(NumericValue).columns.unit, part.name, name
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
            usage = self.unit_part_usage(unit_type_name, part.name)
            if usage:
                raise ValueError(f"unit part {part.name!r} still has {usage} values")
            _ = Database.execute(sqla.delete(UnitPart).where(c.uuid == part.uuid))
        Database.flush()
