"""The enum_options table: EnumOption (mapped Row) + EnumOptions (store).

Cross-table sync (option draft + value propagation) lives in
``nylium.objects.navigation.sync_enum_options`` — a table store never
imports a sibling table (ADR-0033).
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database.table import Row, Table
from nylium.tables.base import reg


@reg.mapped_as_dataclass
class EnumOption(Row):
    __tablename__: ClassVar[str] = "enum_options"
    __table_args__: ClassVar[tuple[object, ...]] = (
        UniqueConstraint("type_uuid", "value"),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, kw_only=True)
    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class EnumOptions(Table[UUID, EnumOption]):
    """The enum_options table as a Mapping of writable options."""

    __row__: ClassVar[type[Row]] = EnumOption


enum_options = EnumOptions()
