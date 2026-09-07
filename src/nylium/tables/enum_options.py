# Options of a string-enum type. The enum type itself is a `types` row
# with kind="enum"; its allowed values are these rows. Option values
# are what enum-typed props store in string_values — renaming an option
# rewrites those rows too.
from collections.abc import Generator
from typing import ClassVar, cast
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.sessioncontext import SessionContext
from nylium.database.tabledomain import TableDomain, TableMapping, tableproperty
from nylium.tables.base import Base
from nylium.tables.string_values import TABLE_StringValues
from nylium.tables.props import TABLE_Props


class TABLE_EnumOptions(Base):
    __tablename__: str = "enum_options"
    __table_args__: tuple[UniqueConstraint, ...] = (
        UniqueConstraint("type_uuid", "value"),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class EnumOption(TableDomain):
    """One enum option: a writable snapshot of a TABLE_EnumOptions row."""

    __table__: ClassVar[type[Base]] = TABLE_EnumOptions

    uuid: tableproperty[UUID] = tableproperty()
    type_uuid: tableproperty[UUID] = tableproperty()
    value: tableproperty[str] = tableproperty()
    position: tableproperty[int] = tableproperty()


class EnumOptions(TableMapping[UUID, EnumOption]):
    """The enum_options table as a Mapping of writable options."""

    __domain__: ClassVar[type[TableDomain]] = EnumOption

    def list_for(self, type_uuid: UUID) -> Generator[EnumOption, None, None]:
        """The options of one enum type, in display order, lazily."""
        with SessionContext():
            options = [
                cast(EnumOption, EnumOption.from_row(row))
                for row in Database.session.scalars(
                    sqla.select(TABLE_EnumOptions)
                    .where(TABLE_EnumOptions.type_uuid == type_uuid)
                    .order_by(TABLE_EnumOptions.position)
                )
            ]
        yield from options

    @databasemethod(commit=False)
    def values_of(self, type_uuid: UUID) -> list[str]:
        return list(
            Database.session.scalars(
                sqla.select(TABLE_EnumOptions.value)
                .where(TABLE_EnumOptions.type_uuid == type_uuid)
                .order_by(TABLE_EnumOptions.position)
            ).all()
        )

    @databasemethod(commit=False)
    def count_usage(self, type_uuid: UUID, value: str) -> int:
        """How many stored prop values currently equal this option."""
        return int(
            Database.session.scalar(
                sqla.select(sqla.func.count())
                .select_from(TABLE_StringValues)
                .join(TABLE_Props, TABLE_StringValues.prop_uuid == TABLE_Props.uuid)
                .where(
                    TABLE_Props.value_type_uuid == type_uuid,
                    TABLE_StringValues.value == value,
                )
            )
            or 0
        )

    @databasemethod(commit=True)
    def sync(self, type_uuid: UUID, items: list[tuple[UUID | None, str]]) -> None:
        """Apply the editor's full option draft, mirroring Props.sync_schema:
        a matching uuid renames the option in place (the rename rewrites
        stored string_values), None creates, omitted options are deleted —
        but a delete refuses while the option is still in use."""
        existing = {
            row.uuid: row
            for row in Database.session.scalars(
                sqla.select(TABLE_EnumOptions).where(
                    TABLE_EnumOptions.type_uuid == type_uuid
                )
            )
        }
        kept = {uuid for uuid, _ in items if uuid is not None}
        for stale_uuid, stale_row in existing.items():
            if stale_uuid in kept:
                continue
            usage = self.count_usage(type_uuid, stale_row.value)
            if usage:
                raise ValueError(
                    f"option {stale_row.value!r} is still used by {usage} values"
                )
            Database.session.delete(stale_row)
        Database.session.flush()
        for position, (option_uuid, value) in enumerate(items):
            if option_uuid is None or option_uuid not in existing:
                Database.session.add(
                    TABLE_EnumOptions(
                        uuid=uuid4(),
                        type_uuid=type_uuid,
                        value=value,
                        position=position,
                    )
                )
                continue
            row = existing[option_uuid]
            if row.value != value:
                _ = Database.session.execute(
                    sqla.update(TABLE_StringValues)
                    .where(
                        TABLE_StringValues.value == row.value,
                        TABLE_StringValues.prop_uuid.in_(
                            sqla.select(TABLE_Props.uuid).where(
                                TABLE_Props.value_type_uuid == type_uuid
                            )
                        ),
                    )
                    .values(value=value)
                )
                row.value = value
            row.position = position
        Database.session.flush()


enum_options = EnumOptions()
