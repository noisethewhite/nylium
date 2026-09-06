from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database
from nylium.database.databasemethod import databasemethod
from nylium.tables.base import Base


class Types(Base):
    __tablename__: str = "types"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # NULL for builtins and array types — only user types carry both forms
    plural_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Material Symbols name, rendered monochrome by the UI;
    # server defaults backfill existing rows on ALTER
    icon: Mapped[str] = mapped_column(
        Text, nullable=False, default="inventory_2", server_default="inventory_2"
    )
    # ADR-0005: stores #RRGGBB hex; the default must match WColor.DEFAULT
    # (tables must not import objects — keep the literal in sync by hand)
    color: Mapped[str] = mapped_column(
        Text, nullable=False, default="#9e9e9e", server_default="#9e9e9e"
    )
    # "object" (regular, builtin or array) | "enum" (string enum — its
    # values live in enum_options; instances never exist for enum types)
    kind: Mapped[str] = mapped_column(
        Text, nullable=False, default="object", server_default="object"
    )
    # Composition flag (ADR-0004): embedded types instantiate only as a
    # prop value of an owner object, never standalone. Orthogonal to
    # kind — an embedded type is still kind="object".
    embedded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    @classmethod
    @databasemethod(commit=False)
    def name_by_uuid(cls, uuid: UUID) -> str | None:
        row = Database.session.get(cls, uuid)
        return None if row is None else row.name

    @classmethod
    @databasemethod(commit=False)
    def uuid_by_name(cls, name: str) -> UUID | None:
        row = Database.session.scalar(
            sqla.select(cls).where(
                cls.name == name
            )
        )
        return None if row is None else row.uuid

    @classmethod
    @databasemethod(commit=False)
    def all_names(cls,) -> list[str]:
        return list(Database.session.scalars(sqla.select(cls.name)).all())

    @classmethod
    @databasemethod(commit=True)
    def update(
        cls,
        uuid: UUID,
        name: str,
        plural_name: str | None,
        icon: str,
        color: str,
    ) -> None:
        row = Database.session.get(cls, uuid)
        if row is None:
            raise KeyError(f"no type with uuid {uuid}")
        row.name = name
        row.plural_name = plural_name
        row.icon = icon
        row.color = color
        Database.session.flush()

    @classmethod
    @databasemethod(commit=True)
    def delete_by_uuid(cls, uuid: UUID) -> None:
        row = Database.session.get(cls, uuid)
        if row is not None:
            Database.session.delete(row)  # its props cascade
