# Parts of a user-defined unit type (`types.kind = 'unit'`): the base
# part plus secondary parts with an affine conversion factor
# (`base = (entered - offset) / multiplier`, so 32°F at 1.8/32 is 0°C).
# Numeric props parameterize on the unit as `Numeric<Temperature>`;
# stored values live in numeric_values — canonical magnitude in `value`,
# the part name as entered in `unit`.
from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.tables.base import Base
from nylium.tables.numeric_values import NumericValues
from nylium.tables.props import Props
from nylium.tables.types import Types


class UnitParts(Base):
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

    @classmethod
    @databasemethod(commit=False)
    def list_for(cls, type_uuid: UUID) -> list["UnitParts"]:
        return list(
            Database.session.scalars(
                sqla.select(cls)
                .where(cls.type_uuid == type_uuid)
                .order_by(cls.position)
            ).all()
        )

    @classmethod
    @databasemethod(commit=False)
    def by_name(cls, type_uuid: UUID, name: str) -> "UnitParts | None":
        return Database.session.scalar(
            sqla.select(cls).where(cls.type_uuid == type_uuid, cls.name == name)
        )

    @classmethod
    @databasemethod(commit=False)
    def base_of(cls, type_uuid: UUID) -> "UnitParts | None":
        return Database.session.scalar(
            sqla.select(cls).where(cls.type_uuid == type_uuid, cls.is_base.is_(True))
        )

    @classmethod
    def names_of(cls, type_uuid: UUID) -> list[str]:
        return [part.name for part in cls.list_for(type_uuid)]

    @classmethod
    @databasemethod(commit=False)
    def usage_count(cls, unit_type_name: str, part_name: str) -> int:
        """Numeric values stored under this part. Values reference a part
        through their prop's parameterized type row (`Numeric<unit>`);
        the name convention lives on WType.unit_numeric_name and is
        repeated here because tables must not import the object layer."""
        parameterized_uuid = Types.uuid_by_name(f"Numeric<{unit_type_name}>")
        if parameterized_uuid is None:
            return 0
        return cls._count_stored(parameterized_uuid, part_name)

    @classmethod
    @databasemethod(commit=False)
    def usage_total(cls, unit_type_name: str) -> int:
        """Every stored value of the unit, any part (or none)."""
        parameterized_uuid = Types.uuid_by_name(f"Numeric<{unit_type_name}>")
        if parameterized_uuid is None:
            return 0
        return cls._count_stored(parameterized_uuid, None)

    @classmethod
    def _count_stored(
        cls, parameterized_uuid: UUID, part_name: str | None
    ) -> int:
        conditions = [
            Props.value_type_uuid == parameterized_uuid,
            NumericValues.prop_uuid == Props.uuid,
        ]
        if part_name is not None:
            conditions.append(NumericValues.unit == part_name)
        return int(
            Database.session.scalar(sqla.select(sqla.func.count()).select_from(NumericValues).where(*conditions))
            or 0
        )

    @classmethod
    @databasemethod(commit=True)
    def sync(
        cls,
        type_uuid: UUID,
        unit_type_name: str,
        items: list[tuple[UUID | None, str, Decimal, Decimal, bool]],
    ) -> None:
        """Apply the full part draft at once: matching uuid edits in place
        (a rename propagates to stored values), None creates, absent parts
        are deleted unless still in use. Validation of the draft itself
        (exactly one base, unique names, nonzero multipliers) is the
        caller's job."""
        existing = cls.list_for(type_uuid)
        by_uuid = {part.uuid: part for part in existing}
        seen: set[UUID] = set()
        for position, (uuid, name, multiplier, offset, is_base) in enumerate(items):
            part = by_uuid.get(uuid) if uuid is not None else None
            if part is None:
                part = cls(uuid=uuid4(), type_uuid=type_uuid, name=name)
                Database.session.add(part)
            elif part.name != name:
                cls._propagate_rename(unit_type_name, part.name, name)
                part.name = name
            part.multiplier = multiplier
            part.offset = offset
            part.is_base = is_base
            part.position = position
            seen.add(part.uuid)
        for part in existing:
            if part.uuid in seen:
                continue
            usage = cls.usage_count(unit_type_name, part.name)
            if usage:
                raise ValueError(
                    f"unit part {part.name!r} still has {usage} values"
                )
            Database.session.delete(part)
        Database.session.flush()

    @classmethod
    def _propagate_rename(
        cls, unit_type_name: str, old_name: str, new_name: str
    ) -> None:
        parameterized_uuid = Types.uuid_by_name(f"Numeric<{unit_type_name}>")
        if parameterized_uuid is None:
            return
        _ = Database.session.execute(
            sqla.update(NumericValues)
            .where(
                NumericValues.prop_uuid.in_(
                    sqla.select(Props.uuid).where(
                        Props.value_type_uuid == parameterized_uuid
                    )
                ),
                NumericValues.unit == old_name,
            )
            .values(unit=new_name)
        )
