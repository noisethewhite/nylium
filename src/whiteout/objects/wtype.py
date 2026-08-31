"""WType: handle on a row of the `types` table.

Owns the type-name conventions, including the generic array type name
(`Array<Element>`) shared by class materialization and attribute IO.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from whiteout.database.tables import Types

if TYPE_CHECKING:
    from whiteout.objects.wprop import WProp


class WType:
    ARRAY_TYPE_PREFIX = "Array<"

    def __init__(self, row: Types):
        self._row = row

    @property
    def uuid(self) -> UUID:
        return self._row.uuid

    @property
    def name(self) -> str:
        return self._row.name

    # --- type-name conventions ---

    @classmethod
    def array_name(cls, element_name: str) -> str:
        return f"{cls.ARRAY_TYPE_PREFIX}{element_name}>"

    @classmethod
    def is_array_name(cls, name: str) -> bool:
        return name.startswith(cls.ARRAY_TYPE_PREFIX) and name.endswith(">")

    @classmethod
    def element_name(cls, array_name: str) -> str:
        return array_name[len(cls.ARRAY_TYPE_PREFIX) : -1]

    # --- row access ---

    @classmethod
    def by_name(cls, session: Session, name: str) -> "WType | None":
        row = session.scalar(sqla.select(Types).where(Types.name == name))
        return None if row is None else cls(row)

    @classmethod
    def by_uuid(cls, session: Session, uuid: UUID) -> "WType | None":
        row = session.get(Types, uuid)
        return None if row is None else cls(row)

    @classmethod
    def ensure(cls, session: Session, name: str) -> "WType":
        existing = cls.by_name(session, name)
        if existing is not None:
            return existing
        row = Types(uuid=uuid4(), name=name)
        session.add(row)
        session.flush()
        return cls(row)

    # --- props of this type ---

    def prop(self, session: Session, key: str) -> "WProp | None":
        from whiteout.objects.wprop import WProp

        return WProp.by_key(session, self, key)

    def props(self, session: Session) -> "list[WProp]":
        from whiteout.objects.wprop import WProp

        rows = session.scalars(
            sqla.select(WProp.ROW).where(WProp.ROW.owner_type_uuid == self.uuid)
        ).all()
        return [WProp(row) for row in rows]

    def ensure_prop(self, session: Session, key: str, value_type: "WType") -> "WProp":
        from whiteout.objects.wprop import WProp

        return WProp.ensure(session, self, key, value_type)
