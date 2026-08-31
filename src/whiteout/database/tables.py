import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, Text, func, Integer, null
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Types(Base):
    __tablename__: str = "types"

    uuid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)


class Props(Base):
    __tablename__: str = "props"

    uuid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    owner_type_uuid: Mapped[uuid.UUID] = mapped_column(nullable=False)
    value_type_uuid: Mapped[uuid.UUID] = mapped_column(nullable=False)


# Instances of types
# (Both arrays and scalars are considered types, too)
class Instances(Base):
    __tablename__: str = "instances"

    uuid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    type_uuid: Mapped[uuid.UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)


# === Values ===


class ArrayValues(Base):
    __tablename__: str = "array_values"

    inst_uuid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    index: Mapped[int] =  mapped_column(Integer, primary_key=True)
    value_uuid: Mapped[uuid.UUID] = mapped_column(nullable=False)


class InstanceValues(Base):
    __tablename__: str = "instance_values"

    uuid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    prop_uuid: Mapped[uuid.UUID] = mapped_column(nullable=False)
    inst_uuid: Mapped[uuid.UUID] = mapped_column(nullable=False)


class StringValues(Base):
    __tablename__: str = "string_values"

    inst_uuid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    prop_uuid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class IntegerValues(Base):
    __tablename__: str = "integer_values"

    inst_uuid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    prop_uuid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)


class DatetimeValues(Base):
    __tablename__: str = "datetime_values"

    inst_uuid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    prop_uuid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    value: Mapped[datetime] = mapped_column(DateTime, nullable=False)
