"""WProp: handle on a row of the `props` table."""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from whiteout.database.tables import Props

if TYPE_CHECKING:
    from whiteout.objects.wtype import WType


class WProp:
    ROW = Props

    def __init__(self, row: Props):
        self._row = row

    @property
    def uuid(self) -> UUID:
        return self._row.uuid

    @property
    def key(self) -> str:
        return self._row.key

    @classmethod
    def by_key(cls, session: Session, owner: "WType", key: str) -> "WProp | None":
        row = session.scalar(
            sqla.select(Props).where(
                Props.owner_type_uuid == owner.uuid, Props.key == key
            )
        )
        return None if row is None else cls(row)

    @classmethod
    def ensure(
        cls, session: Session, owner: "WType", key: str, value_type: "WType"
    ) -> "WProp":
        existing = cls.by_key(session, owner, key)
        if existing is not None:
            existing._row.value_type_uuid = value_type.uuid
            return existing
        row = Props(
            uuid=uuid4(),
            key=key,
            owner_type_uuid=owner.uuid,
            value_type_uuid=value_type.uuid,
        )
        session.add(row)
        session.flush()
        return cls(row)

    def value_type(self, session: Session) -> "WType":
        from whiteout.objects.wtype import WType

        value_type = WType.by_uuid(session, self._row.value_type_uuid)
        if value_type is None:
            raise RuntimeError(f"prop {self.key!r} has dangling value type")
        return value_type
