# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

# Parts of a user-defined unit type (`types.kind = 'unit'`): the base
# part plus secondary parts with an affine conversion factor
# (`base = (entered - offset) / multiplier`, so 32°F at 1.8/32 is 0°C).
# Numeric props parameterize on the unit as `Numeric<Temperature>`;
# stored values live in numeric_values — canonical magnitude in `value`,
# the part name as entered in `unit`.
from decimal import Decimal
from typing import ClassVar
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.base import reg
from nylium.tables.values.numeric_values import TABLE_NumericValues
from nylium.tables.objects.props import TABLE_Props
from nylium.tables.objects.typeref import TABLE_Types

# TABLE_Types comes from typeref.py, not types.py: types.py imports this
# module for Type.unit_parts, so importing the domain layer back would
# cycle. Parameterized-type resolution is a plain SQL select.


def _parameterized_uuid(unit_type_name: str) -> UUID | None:
    """The `Numeric<unit>` type row's uuid, or None when it doesn't exist."""
    return Database.session.scalar(
        sqla.select(TABLE_Types.uuid).where(
            TABLE_Types.name == f"Numeric<{unit_type_name}>"
        )
    )


@reg.mapped_as_dataclass
class TABLE_UnitParts:
    __tablename__: ClassVar[str] = "unit_parts"
    __table_args__: ClassVar[tuple[object, ...]] = (
        # Part names are unique within their unit — values reference them
        # by (prop type, part name), so ambiguity would corrupt reads
        UniqueConstraint("type_uuid", "name"),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
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


class UnitPart(Row):
    """One unit part: a writable snapshot of a TABLE_UnitParts row."""

    __table__: ClassVar[type[object]] = TABLE_UnitParts

    uuid: UUID
    type_uuid: UUID
    name: str
    multiplier: Decimal
    offset: Decimal
    is_base: bool
    position: int

    def wire(self) -> dict[str, object]:
        """The JSON-safe wire shape: Decimals cross as strings, matching
        web/src/contracts.ts UnitPartView."""
        return {
            "uuid": str(self.uuid),
            "name": self.name,
            "multiplier": str(self.multiplier),
            "offset": str(self.offset),
            "is_base": self.is_base,
        }


class UnitParts(Table[UUID, UnitPart]):
    """The unit_parts table as a Mapping of writable parts."""

    __row__: ClassVar[type[Row]] = UnitPart

    @databasemethod(commit=False)
    def usage_count(self, unit_type_name: str, part_name: str | None = None) -> int:
        """Numeric values stored under this part (or, with None, any part
        of the unit). Values reference a part through their prop's
        parameterized type row (`Numeric<unit>`); the name convention
        lives on WType.unit_numeric_name and is repeated here because
        tables must not import the object layer."""
        parameterized_uuid = _parameterized_uuid(unit_type_name)
        if parameterized_uuid is None:
            return 0
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
        existing = sorted(self.where(type_uuid=type_uuid), key=lambda p: p.position)
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
                part = UnitPart(row)
            else:
                if part.name != name:
                    parameterized_uuid = _parameterized_uuid(unit_type_name)
                    if parameterized_uuid is not None:
                        _ = Database.session.execute(
                            sqla.update(TABLE_NumericValues)
                            .where(
                                TABLE_NumericValues.prop_uuid.in_(
                                    sqla.select(TABLE_Props.uuid).where(
                                        TABLE_Props.value_type_uuid
                                        == parameterized_uuid,
                                    )
                                ),
                                TABLE_NumericValues.unit == part.name,
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
            usage = self.usage_count(unit_type_name, part.name)
            if usage:
                raise ValueError(
                    f"unit part {part.name!r} still has {usage} values"
                )
            _ = Database.session.execute(
                sqla.delete(TABLE_UnitParts).where(TABLE_UnitParts.uuid == part.uuid)
            )
        Database.session.flush()


unit_parts = UnitParts()
