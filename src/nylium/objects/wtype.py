"""WType: handle on a row of the `types` table.

Owns the type-name conventions, including the generic array type name
(`Array<Element>`) shared by class materialization and attribute IO.

Prop queries live on WProp, not here: wprop imports wtype (for
value_type), so wtype must not import wprop back — that keeps the
objects package a DAG.
"""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from nylium.database import Database, Types


class WType:
    ARRAY_TYPE_PREFIX: ClassVar[str] = "Array<"

    def __init__(self, row: Types):
        # snapshot, not a live row: reads must not depend on the session
        # that fetched the row still being open
        self._uuid: UUID = row.uuid
        self._name: str = row.name
        self._plural_name: str | None = row.plural_name
        self._icon: str = row.icon
        self._color: str = row.color

    @property
    def uuid(self) -> UUID:
        return self._uuid

    @property
    def name(self) -> str:
        return self._name

    @property
    def plural_name(self) -> str | None:
        return self._plural_name

    @property
    def icon(self) -> str:
        return self._icon

    @property
    def color(self) -> str:
        return self._color

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
    @Database.sessionmethod(bundled=False, commit=False)
    def by_name(cls, session: Session, name: str) -> "WType | None":
        row = session.scalar(sqla.select(Types).where(Types.name == name))
        return None if row is None else cls(row)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_uuid(cls, session: Session, uuid: UUID) -> "WType | None":
        row = session.get(Types, uuid)
        return None if row is None else cls(row)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def ensure(
        cls,
        session: Session,
        name: str,
        plural_name: str | None = None,
        icon: str | None = None,
    ) -> "WType":
        existing = cls.by_name(name)
        if existing is not None:
            return existing
        row = Types(uuid=uuid4(), name=name, plural_name=plural_name)
        if icon is not None:
            row.icon = icon
        session.add(row)
        session.flush()
        return cls(row)
