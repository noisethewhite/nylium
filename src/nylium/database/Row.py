"""The ``Row`` type — one mapped dataclass row (ADR-0033).

A ``Row`` IS the mapped dataclass: each concrete Row subclass is decorated
``@reg.mapped_as_dataclass`` and carries its own ``mapped_column`` schema.
There is no separate ``TABLE_*`` raw mapping and no explicit write-through
UPDATE — attribute writes go through SQLAlchemy's change tracking and are
flushed/committed by the caller's transaction context.

``get_mapper`` is the shared generic wrapper around ``sqlalchemy.inspect``.
"""
from __future__ import annotations

from typing import TypeVar, cast

from typing_extensions import override

import sqlalchemy as sqla
from sqlalchemy.orm import InstanceState, Mapper

from nylium.database.SessionContext import SessionContext

_M = TypeVar("_M")


def get_mapper(mapped: type[_M]) -> Mapper[_M]:
    """SQLAlchemy's ``inspect``, narrowed to ``Mapper`` (with a clear error)."""
    inspected = sqla.inspect(mapped)
    if not isinstance(inspected, Mapper):
        raise TypeError(f"{mapped!r} is not a mapped class")
    return cast("Mapper[_M]", inspected)


class Row:
    """A mapped dataclass snapshot.

    Subclasses are ``@reg.mapped_as_dataclass`` dataclasses that declare
    their own schema. ``row["name"]`` reads, ``row["name"] = value`` writes
    through SQLAlchemy change tracking (flushed/committed by the caller's
    transaction context).
    """

    @classmethod
    def pk_name(cls) -> str:
        """The single primary-key column name (used for Mapping iteration)."""
        return cast(str, get_mapper(cls).primary_key[0].name)

    def __getitem__(self, name: str) -> object:
        return cast(object, getattr(self, name))

    def __setitem__(self, name: str, value: object) -> None:
        setattr(self, name, value)

    @override
    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        self._autopersist()

    def _autopersist(self) -> None:
        """ADR-0010: a standalone attribute write persists itself.

        Inside an ambient session (``use_same_session`` /
        ``commit_after_this``) the write stays a dirty mark and the
        session owner commits once at the end. Only a row written with NO
        ambient session merges + commits on its own — this is what makes
        ``row.name = "x"`` outside any decorator durable, without the
        premature commits that plagued the old per-write persist.
        """
        if SessionContext.has_session():
            return
        state = cast("InstanceState[object]", sqla.inspect(self))
        if not (state.persistent or state.detached):
            return  # transient/pending: construction, not a write
        with SessionContext():
            session = SessionContext.get_session()
            _ = session.merge(self)
            session.commit()
