"""TypeUUID — typed identifier for a ``Type`` row (``types``)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sqla
from pydantic_core import core_schema

from nylium.database import Database
from nylium.database.Row import mapper
from nylium.data.rows import EnumOption, NumericValue, Prop, StringValue, Type, UnitPart
from nylium.data.tables import (
    enum_options,
    props,
    traits,
    type_decor,
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
        return type_decor[self].plural_name

    def icon(self) -> str:
        return type_decor[self].icon

    def color(self) -> str:
        return type_decor[self].color

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

    # --- enum options ---

    @Database.use_same_session
    def _enum_option_usage(self, value: str) -> int:
        sv_c = mapper(StringValue).columns
        p_c = mapper(Prop).columns
        return int(
            Database.scalar(
                sqla.select(sqla.func.count())
                .select_from(StringValue)
                .join(Prop, sv_c.prop_uuid == p_c.uuid)
                .where(p_c.value_type_uuid == self, sv_c.value == value)
            )
            or 0
        )

    @Database.commit_after_this
    def sync_enum_options(self, items: list[tuple[UUID | None, str]]) -> None:
        """Apply the enum editor's full option draft: matching uuid renames
        (propagating to stored values), None creates, absent options are
        deleted unless still in use."""
        c = mapper(EnumOption).columns
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
                sv_c = mapper(StringValue).columns
                p_c = mapper(Prop).columns
                _ = Database.execute(
                    sqla.update(StringValue)
                    .where(
                        sv_c.value == row.value,
                        sv_c.prop_uuid.in_(
                            sqla.select(p_c.uuid).where(p_c.value_type_uuid == self)
                        ),
                    )
                    .values(value=value)
                )
                row.value = value
            row.position = position
        Database.flush()

    # --- unit parts ---

    @classmethod
    @Database.use_same_session
    def parameterized_numeric(cls, unit_type_name: str) -> "TypeUUID | None":
        """The uuid of the ``Numeric<Unit>`` parameterized type row."""
        t_c = mapper(Type).columns
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
        p_c = mapper(Prop).columns
        nv_c = mapper(NumericValue).columns
        conditions: list[sqla.ColumnElement[bool]] = [
            p_c.value_type_uuid == parameterized,
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
        self,
        unit_type_name: str,
        items: list[tuple[UUID | None, str, Decimal, Decimal, bool]],
    ) -> None:
        """Apply the unit editor's full part draft: matching uuid edits in
        place (a rename propagates to stored values), None creates, absent
        parts are deleted unless still in use."""
        c = mapper(UnitPart).columns
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
                        p_c = mapper(Prop).columns
                        nv_c = mapper(NumericValue).columns
                        _ = Database.execute(
                            sqla.update(NumericValue)
                            .where(
                                nv_c.prop_uuid.in_(
                                    sqla.select(p_c.uuid).where(
                                        p_c.value_type_uuid == parameterized,
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
            usage = self.unit_part_usage(unit_type_name, part.name)
            if usage:
                raise ValueError(f"unit part {part.name!r} still has {usage} values")
            _ = Database.execute(sqla.delete(UnitPart).where(c.uuid == part.uuid))
        Database.flush()
