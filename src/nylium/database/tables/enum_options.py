# Options of a string-enum type. The enum type itself is a `types` row
# with kind="enum"; its allowed values are these rows. Option values
# are what enum-typed props store in string_values — renaming an option
# rewrites those rows too.
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, Session, mapped_column

from nylium.database.database import Database
from nylium.database.tables.base import Base
from nylium.database.tables.string_values import StringValues
from nylium.database.tables.props import Props


class EnumOptions(Base):
    __tablename__: str = "enum_options"
    __table_args__: tuple[UniqueConstraint, ...] = (UniqueConstraint("type_uuid", "value"),)

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def list_for(cls, session: Session, type_uuid: UUID) -> list["EnumOptions"]:
        return list(
            session.scalars(
                sqla.select(cls)
                .where(cls.type_uuid == type_uuid)
                .order_by(cls.position)
            ).all()
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def values_of(cls, session: Session, type_uuid: UUID) -> list[str]:
        return list(
            session.scalars(
                sqla.select(cls.value)
                .where(cls.type_uuid == type_uuid)
                .order_by(cls.position)
            ).all()
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def count_usage(cls, session: Session, type_uuid: UUID, value: str) -> int:
        """How many stored prop values currently equal this option."""
        return int(
            session.scalar(
                sqla.select(sqla.func.count())
                .select_from(StringValues)
                .join(Props, StringValues.prop_uuid == Props.uuid)
                .where(Props.value_type_uuid == type_uuid, StringValues.value == value)
            ) or 0
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def sync(
        cls, session: Session, type_uuid: UUID, items: list[tuple[UUID | None, str]]
    ) -> None:
        """Apply the editor's full option draft, mirroring Props.sync_schema:
        a matching uuid renames the option in place (the rename rewrites
        stored string_values), None creates, omitted options are deleted —
        but a delete refuses while the option is still in use."""
        existing = {
            row.uuid: row
            for row in session.scalars(
                sqla.select(cls).where(cls.type_uuid == type_uuid)
            )
        }
        kept = {uuid for uuid, _ in items if uuid is not None}
        for stale_uuid, stale_row in existing.items():
            if stale_uuid in kept:
                continue
            usage = cls.count_usage(type_uuid, stale_row.value)
            if usage:
                raise ValueError(
                    f"option {stale_row.value!r} is still used by {usage} values"
                )
            session.delete(stale_row)
        session.flush()
        for position, (option_uuid, value) in enumerate(items):
            if option_uuid is None or option_uuid not in existing:
                session.add(
                    cls(uuid=uuid4(), type_uuid=type_uuid, value=value, position=position)
                )
                continue
            row = existing[option_uuid]
            if row.value != value:
                _ = session.execute(
                    sqla.update(StringValues)
                    .where(
                        StringValues.value == row.value,
                        StringValues.prop_uuid.in_(
                            sqla.select(Props.uuid).where(Props.value_type_uuid == type_uuid)
                        ),
                    )
                    .values(value=value)
                )
                row.value = value
            row.position = position
        session.flush()
