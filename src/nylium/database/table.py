"""Rows and table Mappings — the whole SQL seam in one place.

A ``Row`` is a dataclass-flavoured snapshot of one mapped row: the
constructor copies every column out of the SQLAlchemy object, attribute
and item access read the snapshot, and assignment (``row.name = x`` or
``row["name"] = x``) writes through to the database with an UPDATE.
The primary key is identity: set at creation, never written through.

A ``Table`` is ``Mapping[K, Row]`` over one mapped class: ``table[key]``
SELECTs and constructs the Row, ``table.where(**eq)`` is the single
reverse-lookup every table answers with, and ``table.all()`` is
``where()`` with no criteria. Concrete tables live next to their mapped
class in ``nylium/tables/`` and add only real business operations
(``create``/``sync``/``delete``); SQLAlchemy never leaves this module
and those.

This module imports no ``nylium.tables`` code — importing a table's
package triggers ``tables/__init__``, which reaches back for ``Row`` /
``Table`` (an import cycle). ``Base`` is a TYPE_CHECKING-only reference.
"""
from __future__ import annotations

from collections.abc import Generator, Iterator, Mapping
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar, cast, override

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.databasemethod import databasemethod
from nylium.database.sessioncontext import SessionContext

if TYPE_CHECKING:
    from nylium.tables.base import Base

_K = TypeVar("_K")
_R = TypeVar("_R", bound="Row")


class Row:
    """A writable snapshot of one mapped row.

    Subclasses set ``__table__`` to their mapped class and annotate the
    columns for typing (``name: str``); the values themselves are plain
    instance attributes copied in by the constructor.
    """

    __table__: ClassVar[type[Base]]

    def __init__(self, row: Base) -> None:
        columns = sqla.inspect(type(row)).columns
        for column in columns:
            object.__setattr__(self, column.name, getattr(row, column.name))

    @classmethod
    def pk_name(cls) -> str:
        """The PK column name (``uuid`` for most, ``token_hash`` /
        ``challenge`` in auth), read off the mapped class."""
        return cast(str, sqla.inspect(cls.__table__).primary_key[0].name)

    @override
    def __setattr__(self, name: str, value: object) -> None:
        object.__setattr__(self, name, value)
        columns = sqla.inspect(self.__table__).columns
        if name in columns and name != self.pk_name():
            self.persist(name, value)

    def __getitem__(self, name: str) -> object:
        return cast(object, getattr(self, name))

    def __setitem__(self, name: str, value: object) -> None:
        setattr(self, name, value)

    @databasemethod(commit=True)
    def persist(self, column: str, value: object) -> None:
        """Write one column through: UPDATE … SET column = value WHERE pk.

        ``commit=True`` joins the owner-commits-once semantics: nested
        writes inside an outer databasemethod share its session and commit
        once at the boundary, so a multi-field edit stays atomic.
        """
        columns = sqla.inspect(self.__table__).columns
        pk = self.pk_name()
        pk_value = cast(object, getattr(self, pk))
        _ = Database.session.execute(
            sqla.update(self.__table__)
            .where(columns[pk] == pk_value)
            .values({column: value})
        )


class Table(Generic[_K, _R], Mapping[_K, _R]):
    """The ``Mapping[K, Row]`` shape of a table.

    Subclasses set ``__row__`` to their concrete Row type. ``_K`` is the
    PK type: ``UUID`` for domain tables, ``str``/``bytes`` for the auth
    session/challenge tables.
    """

    __row__: ClassVar[type[Row]]

    @property
    def _mapped(self) -> type[Base]:
        return self.__row__.__table__

    @databasemethod(commit=False)
    def __getitem__(self, key: _K) -> _R:
        row = Database.session.get(self._mapped, key)
        if row is None:
            raise KeyError(key)
        return cast(_R, self.__row__(row))

    @override
    def __iter__(self) -> Iterator[_K]:
        pk = sqla.inspect(self._mapped).columns[self.__row__.pk_name()]
        with SessionContext():
            keys = list(Database.session.scalars(sqla.select(pk)))
        yield from cast("list[_K]", keys)

    @override
    def __len__(self) -> int:
        with SessionContext():
            return int(
                Database.session.scalar(
                    sqla.select(sqla.func.count()).select_from(self._mapped)
                )
                or 0
            )

    def where(self, **eq: object) -> Generator[_R, None, None]:
        """Every row whose columns equal the given values, lazily.

        The rows are materialised inside one SessionContext (closed before
        the first yield) so a caller that abandons iteration early never
        strands a live connection.
        """
        with SessionContext():
            rows = [
                self.__row__(row)
                for row in Database.session.scalars(
                    sqla.select(self._mapped).filter_by(**eq)
                )
            ]
        yield from cast("list[_R]", rows)

    def all(self) -> Generator[_R, None, None]:
        """Every row, lazily — ``where()`` with no criteria."""
        yield from self.where()
