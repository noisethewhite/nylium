from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from nylium.database.database import Database
from nylium.database.tables.base import Base


class Types(Base):
    __tablename__: str = "types"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # NULL for builtins and array types — only user types carry both forms
    plural_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Material Symbols name + palette key, rendered monochrome by the UI;
    # server defaults backfill existing rows on ALTER
    icon: Mapped[str] = mapped_column(
        Text, nullable=False, default="inventory_2", server_default="inventory_2"
    )
    color: Mapped[str] = mapped_column(
        Text, nullable=False, default="gray", server_default="gray"
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

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def all_names(cls, session: Session) -> list[str]:
        return list(session.scalars(sqla.select(cls.name)).all())

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def update(
        cls,
        session: Session,
        uuid: UUID,
        name: str,
        plural_name: str | None,
        icon: str,
        color: str,
    ) -> None:
        row = session.get(cls, uuid)
        if row is None:
            raise KeyError(f"no type with uuid {uuid}")
        row.name = name
        row.plural_name = plural_name
        row.icon = icon
        row.color = color
        session.flush()

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def delete_by_uuid(cls, session: Session, uuid: UUID) -> None:
        row = session.get(cls, uuid)
        if row is not None:
            session.delete(row)  # its props cascade
