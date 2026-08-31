from uuid import UUID, uuid4
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Types(Base):
    __tablename__: str = "types"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)


class Props(Base):
    __tablename__: str = "props"
    __table_args__: tuple[UniqueConstraint, ...] = (
        # One key can't be defined twice on the same owner type
        UniqueConstraint("owner_type_uuid", "key"),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    owner_type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=False
    )
    value_type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid"), nullable=False
    )


# Instances of types
# (Both arrays and scalars are considered types, too)
class Instances(Base):
    __tablename__: str = "instances"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# === Values ===
# Scalars live in one table per value kind, keyed by (instance, prop).
# No row = the prop has no value on that instance.

class StringValues(Base):
    __tablename__: str = "string_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)


class IntegerValues(Base):
    __tablename__: str = "integer_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False)


class NumericValues(Base):
    __tablename__: str = "numeric_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[Decimal] = mapped_column(nullable=False)


class BooleanValues(Base):
    __tablename__: str = "boolean_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[bool] = mapped_column(nullable=False)


class DatetimeValues(Base):
    __tablename__: str = "datetime_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# Values that are references to other instances (links, nested objects,
# arrays). The referenced instance's own uuid doubles as this row's pk.
class InstanceValues(Base):
    __tablename__: str = "instance_values"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), nullable=False
    )
    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False
    )


# Array elements: the array itself is an instance (of an array type);
# rows map (array instance, index) -> element instance.
class ArrayValues(Base):
    __tablename__: str = "array_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    index: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid"), nullable=False
    )
