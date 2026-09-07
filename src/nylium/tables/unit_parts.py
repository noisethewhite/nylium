# Parts of a user-defined unit type (`types.kind = 'unit'`): the base
# part plus secondary parts with an affine conversion factor
# (`base = (entered - offset) / multiplier`, so 32°F at 1.8/32 is 0°C).
# Numeric props parameterize on the unit as `Numeric<Temperature>`;
# stored values live in numeric_values — canonical magnitude in `value`,
# the part name as entered in `unit`.
#
# ADR-0011: the table's abstraction is a Mapping over writable domain
# objects. `UnitPart` snapshots one row; assigning a tableproperty writes
# through to the table (`part.name = "kg"` issues an UPDATE). Read helpers
# are lazy Generators; the reverse lookup lives on the descriptor itself
# (`UnitPart.name.list_for("kg")`).
from collections.abc import Generator
from decimal import Decimal
from typing import ClassVar, cast
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.sessioncontext import SessionContext
from nylium.database.tabledomain import TableDomain, TableMapping, tableproperty
from nylium.tables.base import Base
from nylium.tables.numeric_values import TABLE_NumericValues
from nylium.tables.props import TABLE_Props
from nylium.tables.types import types


class TABLE_UnitParts(Base):
    __tablename__: str = "unit_parts"
    __table_args__: tuple[UniqueConstraint, ...] = (
        # Part names are unique within their unit — values reference them
        # by (prop type, part name), so ambiguity would corrupt reads
        UniqueConstraint("type_uuid", "name"),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # affine conversion entered -> base: base = (entered - offset) / multiplier
    multiplier: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    offset: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0)
    # exactly one part per unit is the base (identity conversion: 1/0)
    is_base: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class UnitPart(TableDomain):
    """One unit part: a writable snapshot of a TABLE_UnitParts row."""

    __table__: ClassVar[type[Base]] = TABLE_UnitParts

    uuid: tableproperty[UUID] = tableproperty()
    type_uuid: tableproperty[UUID] = tableproperty()
    name: tableproperty[str] = tableproperty()
    multiplier: tableproperty[Decimal] = tableproperty()
    offset: tableproperty[Decimal] = tableproperty()
    is_base: tableproperty[bool] = tableproperty()
    position: tableproperty[int] = tableproperty()


class UnitParts(TableMapping[UUID, UnitPart]):
    """The unit_parts table as a Mapping of writable parts."""

    __domain__: ClassVar[type[TableDomain]] = UnitPart

    def list_for(self, type_uuid: UUID) -> Generator[UnitPart, None, None]:
        """The parts of one unit, in display order, lazily."""
        with SessionContext():
            parts = [
                cast(UnitPart, UnitPart.from_row(row))
                for row in Database.session.scalars(
                    sqla.select(TABLE_UnitParts)
                    .where(TABLE_UnitParts.type_uuid == type_uuid)
                    .order_by(TABLE_UnitParts.position)
                )
            ]
        yield from parts

    @databasemethod(commit=False)
    def by_name(self, type_uuid: UUID, name: str) -> UnitPart | None:
        row = Database.session.scalar(
            sqla.select(TABLE_UnitParts).where(
                TABLE_UnitParts.type_uuid == type_uuid, TABLE_UnitParts.name == name
            )
        )
        if row is None:
            return None
        return cast(UnitPart, UnitPart.from_row(row))

    @databasemethod(commit=False)
    def base_of(self, type_uuid: UUID) -> UnitPart | None:
        row = Database.session.scalar(
            sqla.select(TABLE_UnitParts).where(
                TABLE_UnitParts.type_uuid == type_uuid,
                TABLE_UnitParts.is_base.is_(True),
            )
        )
        if row is None:
            return None
        return cast(UnitPart, UnitPart.from_row(row))

    def names_of(self, type_uuid: UUID) -> list[str]:
        return [part.name for part in self.list_for(type_uuid)]

    @databasemethod(commit=False)
    def usage_count(self, unit_type_name: str, part_name: str) -> int:
        """Numeric values stored under this part. Values reference a part
        through their prop's parameterized type row (`Numeric<unit>`);
        the name convention lives on WType.unit_numeric_name and is
        repeated here because tables must not import the object layer."""
        parameterized = types.by_name(f"Numeric<{unit_type_name}>")
        if parameterized is None:
            return 0
        return self._count_stored(parameterized.uuid, part_name)

    @databasemethod(commit=False)
    def usage_total(self, unit_type_name: str) -> int:
        """Every stored value of the unit, any part (or none)."""
        parameterized = types.by_name(f"Numeric<{unit_type_name}>")
        if parameterized is None:
            return 0
        return self._count_stored(parameterized.uuid, None)

    def _count_stored(
        self, parameterized_uuid: UUID, part_name: str | None
    ) -> int:
        conditions = [
            TABLE_Props.value_type_uuid == parameterized_uuid,
            TABLE_NumericValues.prop_uuid == TABLE_Props.uuid,
        ]
        if part_name is not None:
            conditions.append(TABLE_NumericValues.unit == part_name)
        return int(
            Database.session.scalar(
                sqla.select(sqla.func.count())
                .select_from(TABLE_NumericValues)
                .where(*conditions)
            )
            or 0
        )

    @databasemethod(commit=True)
    def sync(
        self,
        type_uuid: UUID,
        unit_type_name: str,
        items: list[tuple[UUID | None, str, Decimal, Decimal, bool]],
    ) -> None:
        """Apply the full part draft at once: matching uuid edits in place
        (a rename propagates to stored values), None creates, absent parts
        are deleted unless still in use. Validation of the draft itself
        (exactly one base, unique names, nonzero multipliers) is the
        caller's job."""
        existing = list(self.list_for(type_uuid))
        by_uuid = {part.uuid: part for part in existing}
        seen: set[UUID] = set()
        for position, (uuid, name, multiplier, offset, is_base) in enumerate(items):
            part = by_uuid.get(uuid) if uuid is not None else None
            if part is None:
                row = TABLE_UnitParts(
                    uuid=uuid4(),
                    type_uuid=type_uuid,
                    name=name,
                    multiplier=multiplier,
                    offset=offset,
                    is_base=is_base,
                    position=position,
                )
                Database.session.add(row)
                Database.session.flush()
                part = cast(UnitPart, UnitPart.from_row(row))
            else:
                if part.name != name:
                    self._propagate_rename(unit_type_name, part.name, name)
                    part.name = name
                part.multiplier = multiplier
                part.offset = offset
                part.is_base = is_base
                part.position = position
            seen.add(part.uuid)
        for part in existing:
            if part.uuid in seen:
                continue
            usage = self.usage_count(unit_type_name, part.name)
            if usage:
                raise ValueError(
                    f"unit part {part.name!r} still has {usage} values"
                )
            self._delete_row(part.uuid)
        Database.session.flush()

    def _delete_row(self, uuid: UUID) -> None:
        _ = Database.session.execute(
            sqla.delete(TABLE_UnitParts).where(TABLE_UnitParts.uuid == uuid)
        )

    def _propagate_rename(
        self, unit_type_name: str, old_name: str, new_name: str
    ) -> None:
        parameterized = types.by_name(f"Numeric<{unit_type_name}>")
        if parameterized is None:
            return
        _ = Database.session.execute(
            sqla.update(TABLE_NumericValues)
            .where(
                TABLE_NumericValues.prop_uuid.in_(
                    sqla.select(TABLE_Props.uuid).where(
                        TABLE_Props.value_type_uuid == parameterized.uuid
                    )
                ),
                TABLE_NumericValues.unit == old_name,
            )
            .values(unit=new_name)
        )


unit_parts = UnitParts()
