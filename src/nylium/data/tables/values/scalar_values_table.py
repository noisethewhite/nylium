"""ScalarValuesTable table store."""
from __future__ import annotations

from typing import ClassVar, Generic, TypeVar, cast
from uuid import UUID
import sqlalchemy as sqla
from nylium.database import Database
from nylium.database.row import Row, mapper
from nylium.database.table import Table
from collections.abc import Callable

_R = TypeVar("_R", bound=Row)

class ScalarValuesTable(Table[tuple[UUID, UUID], _R], Generic[_R]):
    """Shared store shape for the nine scalar value tables.

    ``read`` / ``write`` / ``clear`` operate on RAW storage values; the
    storage <-> python conversion stays with the ``WScalar`` markers
    (``to_storage`` / ``from_storage``).
    """

    __row__: ClassVar[type[Row]]

    @classmethod
    def _table(cls) -> type[Row]:
        """The mapped class — the Row itself (no ``TABLE_*`` indirection)."""
        return cls.__row__

    @classmethod
    @Database.use_same_session
    def read(cls, inst_uuid: UUID, prop_uuid: UUID) -> object:
        """Raw stored value, or None when the cell is absent."""
        row = Database.get(cls._table(), (inst_uuid, prop_uuid))
        return None if row is None else getattr(row, "value")

    @classmethod
    @Database.use_same_session
    def write(cls, inst_uuid: UUID, prop_uuid: UUID, value: object) -> None:
        """Upsert one cell (insert or update in place)."""
        table = cls._table()
        row = Database.get(table, (inst_uuid, prop_uuid))
        if row is None:
            ctor = cast("Callable[..., Row]", table)
            Database.add(ctor(inst_uuid=inst_uuid, prop_uuid=prop_uuid, value=value))
            return
        columns = mapper(table).columns
        _ = Database.execute(
            sqla.update(table)
            .where(columns.inst_uuid == inst_uuid, columns.prop_uuid == prop_uuid)
            .values(value=value)
        )

    @classmethod
    @Database.use_same_session
    def clear(cls, inst_uuid: UUID, prop_uuid: UUID) -> bool:
        """Delete the row if present; True when a row was actually deleted."""
        row = Database.get(cls._table(), (inst_uuid, prop_uuid))
        if row is None:
            return False
        Database.delete(row)
        return True
