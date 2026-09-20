"""The unit_parts table as a Mapping of writable parts (Table class + singleton)."""
from __future__ import annotations

from decimal import Decimal
from typing import ClassVar
from uuid import UUID, uuid4

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.table import Row, Table
from nylium.tables.objects.props import TABLE_Props as TABLE_Props
from nylium.tables.objects.table_types import TABLE_Types as TABLE_Types
from nylium.tables.objects.table_unit_parts import TABLE_UnitParts as TABLE_UnitParts
from nylium.tables.objects.unit_part import UnitPart as UnitPart
from nylium.tables.values.numeric_values import TABLE_NumericValues as TABLE_NumericValues

# TABLE_Types comes from table_types.py, not types.py: types.py imports this
# module for Type.unit_parts, so importing the domain layer back would
# cycle. Parameterized-type resolution is a plain SQL select.


class UnitParts(Table[UUID, UnitPart]):
    """The unit_parts table as a Mapping of writable parts."""

    __row__: ClassVar[type[Row]] = UnitPart

    @classmethod
    def _parameterized_uuid(cls, unit_type_name: str) -> UUID | None:
        """The `Numeric<unit>` type row's uuid, or None when it doesn't exist."""
        return Database.scalar(
            sqla.select(TABLE_Types.uuid).where(
                TABLE_Types.name == f"Numeric<{unit_type_name}>"
            )
        )

    @Database.use_same_session
    def usage_count(self, unit_type_name: str, part_name: str | None = None) -> int:
        """Numeric values stored under this part (or, with None, any part
        of the unit). Values reference a part through their prop's
        parameterized type row (`Numeric<unit>`); the name convention
        lives on WType.unit_numeric_name and is repeated here because
        tables must not import the object layer."""
        parameterized_uuid = self._parameterized_uuid(unit_type_name)
        if parameterized_uuid is None:
            return 0
        conditions = [
            TABLE_Props.value_type_uuid == parameterized_uuid,
            TABLE_NumericValues.prop_uuid == TABLE_Props.uuid,
        ]
        if part_name is not None:
            conditions.append(TABLE_NumericValues.unit == part_name)
        return int(
            Database.scalar(
                sqla.select(sqla.func.count())
                .select_from(TABLE_NumericValues)
                .where(*conditions)
            )
            or 0
        )

    @Database.commit_after_this
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
                Database.add(row)
                Database.flush()
                part = UnitPart(row)
            else:
                if part.name != name:
                    parameterized_uuid = self._parameterized_uuid(unit_type_name)
                    if parameterized_uuid is not None:
                        _ = Database.execute(
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
            _ = Database.execute(
                sqla.delete(TABLE_UnitParts).where(TABLE_UnitParts.uuid == part.uuid)
            )
        Database.flush()


unit_parts = UnitParts()
