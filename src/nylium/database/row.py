"""The ``Row`` snapshot type — one writable row of a mapped table.

A ``Row`` is a dataclass-flavoured snapshot of one mapped row: the
constructor copies every column out of the SQLAlchemy object, attribute
and item access read the snapshot, and assignment (``row.name = x`` or
``row["name"] = x``) writes through to the database with an UPDATE.
The primary key is identity: set at creation, never written through.

``mapper`` is the shared ``TypeVar``-generic wrapper around
``sqlalchemy.inspect`` that both ``Row`` and ``Table`` use to reach a
mapped class's columns. It lives here so ``Table`` can import it without
an import cycle.

This module imports no ``nylium.tables`` code — importing a table's
package triggers ``tables/__init__``, which reaches back for ``Row`` /
``Table`` (an import cycle).
"""
from __future__ import annotations

from typing import ClassVar, TypeVar, cast, override

import sqlalchemy as sqla
from sqlalchemy.orm import Mapper

from nylium.database import Database

_M = TypeVar("_M")


def mapper(mapped: type[_M]) -> Mapper[_M]:
    inspected = sqla.inspect(mapped)
    if not isinstance(inspected, Mapper):
        raise TypeError(f"{mapped!r} is not a mapped class")
    return cast("Mapper[_M]", inspected)


class Row:
    """A writable snapshot of one mapped row.

    Subclasses set ``__table__`` to their mapped class and annotate the
    columns for typing (``name: str``); the values themselves are plain
    instance attributes copied in by the constructor.
    """

    __table__: ClassVar[type[object]]

    def __init__(self, row: object) -> None:
        columns = mapper(type(row)).columns
        for column in columns:
            object.__setattr__(self, column.name, getattr(row, column.name))

    @classmethod
    def pk_name(cls) -> str:
        """The PK column name (``uuid`` for most, ``token_hash`` /
        ``challenge`` in auth), read off the mapped class."""
        return cast(str, mapper(cls.__table__).primary_key[0].name)

    @override
    def __setattr__(self, name: str, value: object) -> None:
        object.__setattr__(self, name, value)
        columns = mapper(self.__table__).columns
        if name in columns and name != self.pk_name():
            self.persist(name, value)

    def __getitem__(self, name: str) -> object:
        return cast(object, getattr(self, name))

    def __setitem__(self, name: str, value: object) -> None:
        setattr(self, name, value)

    @Database.commit_after_this
    def persist(self, column: str, value: object) -> None:
        """Write one column through: UPDATE … SET column = value WHERE pk.

        ``commit_after_this`` joins the owner-commits-once semantics: nested
        writes inside an outer session share its session and commit
        once at the boundary, so a multi-field edit stays atomic.
        """
        columns = mapper(self.__table__).columns
        pk = self.pk_name()
        pk_value = cast(object, getattr(self, pk))
        _ = Database.execute(
            sqla.update(self.__table__)
            .where(columns[pk] == pk_value)
            .values({column: value})
        )
