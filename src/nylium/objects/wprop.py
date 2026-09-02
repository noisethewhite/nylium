"""WProp: handle on a row of the `props` table.

Owns every query against `props` — WType deliberately does not import
WProp, so the dependency direction is wprop -> wtype and nothing cycles.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from nylium.database import Database, Props

if TYPE_CHECKING:
    from nylium.objects.wtype import WType


class WProp:
    ROW: ClassVar[type[Props]] = Props

    _row: Props

    def __init__(self, row: Props):
        # snapshot for reads (session-independent); _row is kept only for
        # the write path in ensure() and is guarded there
        self._row = row
        self._uuid: UUID = row.uuid
        self._key: str = row.key
        self._value_type_uuid: UUID = row.value_type_uuid

    @property
    def uuid(self) -> UUID:
        return self._uuid

    @property
    def key(self) -> str:
        return self._key

    def _live_row(self) -> Props:
        if sqla.inspect(self._row).detached:
            msg = f"prop {self._key!r} wraps a row whose session is gone — writes must run inside a sessionmethod chain"
            raise RuntimeError(msg)
        return self._row

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_key(cls, session: Session, owner: "WType", key: str) -> "WProp | None":
        row = session.scalar(
            sqla.select(Props).where(
                Props.owner_type_uuid == owner.uuid, Props.key == key
            )
        )
        return None if row is None else cls(row)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def all_for(cls, session: Session, owner: "WType") -> "list[WProp]":
        rows = session.scalars(
            sqla.select(Props).where(Props.owner_type_uuid == owner.uuid)
        ).all()
        return [cls(row) for row in rows]

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def ensure(
        cls, session: Session, owner: "WType", key: str, value_type: "WType"
    ) -> "WProp":
        existing = cls.by_key(owner, key)
        if existing is not None:
            existing._live_row().value_type_uuid = value_type.uuid
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

    @Database.sessionmethod(bundled=True, commit=False)
    def value_type(self) -> "WType":
        from nylium.objects.wtype import WType

        value_type = WType.by_uuid(self._value_type_uuid)
        if value_type is None:
            raise RuntimeError(f"prop {self.key!r} has dangling value type")
        return value_type
