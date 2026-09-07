from typing import cast
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.store import Store
from nylium.tables.base import Base
from nylium.tables.types import types


class TABLE_Props(Base):
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
    # the prop's slot in the owner type's display order — create order
    # unless a reorder overwrote it
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # ADR-0005: a formula string over the owner's Array<T> props (e.g.
    # "SUM(items.price) * 1.21"); NULL means a plain stored prop
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ADR-0007: a reference to a Function<T,R> instance whose output type
    # is this prop's value type; the result is computed lazily at read time
    # (like a formula). Mutually exclusive with `formula`.
    function_uuid: Mapped[UUID | None] = mapped_column(nullable=True)


class Props(Store[UUID, TABLE_Props]):
    """Props access layer: rows by uuid plus the owner/value-type indexes."""

    def __init__(self) -> None:
        super().__init__(TABLE_Props)

    @databasemethod(commit=False)
    def count_with_value_type(self, value_type_uuid: UUID) -> int:
        """Props whose value type is this row — the FK stops deletes,
        callers that want a friendly error check here first."""
        return int(
            Database.session.scalar(
                sqla.select(sqla.func.count())
                .select_from(TABLE_Props)
                .where(TABLE_Props.value_type_uuid == value_type_uuid)
            )
            or 0
        )

    @databasemethod(commit=False)
    def get_type_name(self, owner_type_uuid: UUID, key: str) -> str:
        row = Database.session.scalar(
            sqla.select(TABLE_Props).where(
                TABLE_Props.owner_type_uuid == owner_type_uuid, TABLE_Props.key == key
            )
        )
        if row is None:
            owner = types.get(owner_type_uuid)
            owner_name = None if owner is None else owner.name
            raise KeyError(f"type {owner_name!r} has no prop {key!r}")
        value_type = types.get(row.value_type_uuid)
        if value_type is None:
            raise KeyError(f"Type with UUID {row.value_type_uuid} does not exist")
        return value_type.name

    @databasemethod(commit=False)
    def formula_keys(self, owner_type_uuid: UUID) -> set[str]:
        """Keys of the owner type's computed props (ADR-0005) — writes to
        these are refused."""
        rows = Database.session.scalars(
            sqla.select(TABLE_Props.key).where(
                TABLE_Props.owner_type_uuid == owner_type_uuid,
                TABLE_Props.formula.is_not(None),
            )
        ).all()
        return set(rows)

    @databasemethod(commit=False)
    def function_keys(self, owner_type_uuid: UUID) -> set[str]:
        """Keys of the owner type's function-backed props (ADR-0007) —
        writes to these are refused (they are computed by a Function)."""
        rows = Database.session.scalars(
            sqla.select(TABLE_Props.key).where(
                TABLE_Props.owner_type_uuid == owner_type_uuid,
                TABLE_Props.function_uuid.is_not(None),
            )
        ).all()
        return set(rows)

    @databasemethod(commit=False)
    def usages_of_value_type(
        self, value_type_uuid: UUID
    ) -> list[tuple[UUID, str]]:
        """(owner_type_uuid, key) of every prop typed with this row — the
        dependency index for cross-type formula rewrites (ADR-0005)."""
        rows = Database.session.execute(
            sqla.select(TABLE_Props.owner_type_uuid, TABLE_Props.key).where(
                TABLE_Props.value_type_uuid == value_type_uuid
            )
        ).all()
        result: list[tuple[UUID, str]] = []
        for row in rows:
            result.append((cast(UUID, row.owner_type_uuid), cast(str, row.key)))
        return result

    @databasemethod(commit=False)
    def update_formula(self, prop_uuid: UUID, formula: str) -> None:
        """Persist a rewritten formula string (ADR-0005 rename-rewrite)."""
        row = Database.session.get(TABLE_Props, prop_uuid)
        if row is None:
            raise KeyError(f"no prop {prop_uuid}")
        row.formula = formula

    @databasemethod(commit=False)
    def set_function(self, prop_uuid: UUID, function_uuid: UUID | None) -> None:
        """Bind (or unbind, with None) a Function<T,R> instance to a prop —
        the prop becomes function-backed and is computed at read time
        (ADR-0007). Mutually exclusive with `formula`; the caller validates."""
        row = Database.session.get(TABLE_Props, prop_uuid)
        if row is None:
            raise KeyError(f"no prop {prop_uuid}")
        row.function_uuid = function_uuid

    @databasemethod(commit=False)
    def clear_function_references(self, function_uuid: UUID) -> None:
        """Unbind every prop computed through this function — called before
        deleting the function instance so no prop strands a dangling uuid."""
        rows = Database.session.scalars(
            sqla.select(TABLE_Props).where(TABLE_Props.function_uuid == function_uuid)
        ).all()
        for row in rows:
            row.function_uuid = None


props = Props()
