from uuid import UUID, uuid4
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sqla
from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from nylium.database.database import Database


class Base(DeclarativeBase):
    pass


class Types(Base):
    __tablename__: str = "types"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def name_by_uuid(cls, session: Session, uuid: UUID) -> str | None:
        row = session.get(cls, uuid)
        return None if row is None else row.name

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def uuid_by_name(cls, session: Session, name: str) -> UUID | None:
        row = session.scalar(
            sqla.select(cls).where(
                cls.name == name
            )
        )
        return None if row is None else row.uuid


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

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def get_type_name(cls, session: Session, owner_type_uuid: UUID, key: str) -> str:
        row = session.scalar(
            sqla.select(cls).where(
                cls.owner_type_uuid == owner_type_uuid, cls.key == key
            )
        )
        if row is None:
            raise KeyError(f"type {Types.name_by_uuid(owner_type_uuid)!r} has no prop {key!r}")
        value_type = Types.name_by_uuid(row.value_type_uuid)
        if value_type is None:
            raise KeyError(f"Type with UUID {row.value_type_uuid} does not exist")
        return value_type


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

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def get_type_name(cls, session: Session, uuid: UUID) -> str:
        inst = session.get(cls, uuid)
        if inst is None:
            return "<gone>"
        name = Types.name_by_uuid(inst.type_uuid)
        return "<dangling>" if name is None else name


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
