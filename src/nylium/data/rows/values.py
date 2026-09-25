"""Mapped Row classes for the *values tables.

The scalar values share one shape — ``inst_uuid`` + ``prop_uuid`` compose
the primary key, and a single ``value`` column holds the typed payload —
so they collapse onto the ``ScalarValueRow`` base and only declare their
own ``__tablename__`` + ``value`` column. The three structural rows
(``ArrayValue`` — an array element, ``FileValue`` — a file reference,
``InstanceLink`` — an object reference) keep their own keys because they
aren't ``(instance, prop)`` scalar cells.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import ClassVar
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.Row import Row
from nylium.database.registry import reg


@reg.mapped_as_dataclass
class ScalarValueRow(Row):
    """Abstract base for scalar ``(instance, prop)`` value rows."""

    __abstract__: ClassVar[bool] = True

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )


@reg.mapped_as_dataclass
class BooleanValue(ScalarValueRow):
    __tablename__: ClassVar[str] = "boolean_values"
    value: Mapped[bool] = mapped_column(nullable=False)


@reg.mapped_as_dataclass
class DateValue(ScalarValueRow):
    __tablename__: ClassVar[str] = "date_values"
    value: Mapped[date] = mapped_column(Date, nullable=False)


@reg.mapped_as_dataclass
class DatetimeValue(ScalarValueRow):
    __tablename__: ClassVar[str] = "datetime_values"
    value: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


@reg.mapped_as_dataclass
class IntegerValue(ScalarValueRow):
    __tablename__: ClassVar[str] = "integer_values"
    value: Mapped[int] = mapped_column(Integer, nullable=False)


@reg.mapped_as_dataclass
class MonthDayTimeValue(ScalarValueRow):
    __tablename__: ClassVar[str] = "monthdaytime_values"
    value: Mapped[str] = mapped_column(Text, nullable=False)


@reg.mapped_as_dataclass
class MonthDayValue(ScalarValueRow):
    __tablename__: ClassVar[str] = "monthday_values"
    value: Mapped[str] = mapped_column(Text, nullable=False)


@reg.mapped_as_dataclass
class NumericValue(ScalarValueRow):
    __tablename__: ClassVar[str] = "numeric_values"
    value: Mapped[Decimal] = mapped_column(nullable=False)
    # unit part name as entered (for `Numeric<Unit>` props); NULL means
    # the unit's base part or a plain unitless Numeric
    unit: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)


@reg.mapped_as_dataclass
class StringValue(ScalarValueRow):
    __tablename__: ClassVar[str] = "string_values"
    value: Mapped[str] = mapped_column(Text, nullable=False)


@reg.mapped_as_dataclass
class TimeValue(ScalarValueRow):
    __tablename__: ClassVar[str] = "time_values"
    value: Mapped[time] = mapped_column(Time, nullable=False)


@reg.mapped_as_dataclass
class ArrayValue(Row):
    """One element of an array instance — ``value_uuid`` points at a boxed
    instance, ``index`` pins the order."""

    __tablename__: ClassVar[str] = "array_values"
    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    index: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_uuid: Mapped[UUID] = mapped_column(nullable=False)


@reg.mapped_as_dataclass
class FileValue(Row):
    """A file bound into a prop — ``file_uuid`` references the stored blob."""

    __tablename__: ClassVar[str] = "file_values"
    file_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("files.uuid", ondelete="CASCADE"), nullable=False
    )
    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )


@reg.mapped_as_dataclass
class InstanceLink(Row):
    """A many-to-one object reference (ADR-0028): ``uuid`` is the target,
    ``(inst_uuid, prop_uuid)`` is the owner cell."""

    __tablename__: ClassVar[str] = "instance_values"
    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid"), nullable=False, index=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False, primary_key=True
    )
