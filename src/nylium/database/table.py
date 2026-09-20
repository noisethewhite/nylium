"""The ``Table`` Mapping — the read/reverse-lookup half of the SQL seam.

A ``Table`` is ``Mapping[K, Row]`` over one mapped class: ``table[key]``
SELECTs and constructs the Row, ``table.where(**eq)`` is the single
reverse-lookup every table answers with, and ``table.all()`` is
``where()`` with no criteria. Concrete tables live next to their mapped
class in ``nylium/tables/`` and add only real business operations
(``create``/``sync``/``delete``); SQLAlchemy never leaves this module and
those.

``Row`` (the writable snapshot) lives in ``row.py``; it is re-exported
here so ``from nylium.database.table import Row`` keeps working at every
existing import site.

This module imports no ``nylium.tables`` code — importing a table's
package triggers ``tables/__init__``, which reaches back for ``Row`` /
``Table`` (an import cycle).
"""
from __future__ import annotations

from collections.abc import Generator, Iterator, Mapping
from typing import ClassVar, Generic, TypeVar, cast, override

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.row import Row as Row, mapper
from nylium.database.sessioncontext import SessionContext

_K = TypeVar("_K")
_R = TypeVar("_R", bound="Row")


class Table(Generic[_K, _R], Mapping[_K, _R]):
    """The ``Mapping[K, Row]`` shape of a table.

    Subclasses set ``__row__`` to their concrete Row type. ``_K`` is the
    PK type: ``UUID`` for domain tables, ``str``/``bytes`` for the auth
    session/challenge tables.
    """

    __row__: ClassVar[type[Row]]

    @property
    def _mapped(self) -> type[object]:
        return self.__row__.__table__

    @Database.use_same_session
    def __getitem__(self, key: _K) -> _R:
        row = Database.get(self._mapped, key)
        if row is None:
            raise KeyError(key)
        return cast(_R, self.__row__(row))

    @override
    def __iter__(self) -> Iterator[_K]:
        pk = mapper(self._mapped).columns[self.__row__.pk_name()]
        with SessionContext():
            keys = list(Database.scalars(sqla.select(pk)))
        yield from cast("list[_K]", keys)

    @override
    def __len__(self) -> int:
        with SessionContext():
            return int(
                Database.scalar(
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
                for row in Database.scalars(
                    sqla.select(self._mapped).filter_by(**eq)
                )
            ]
        yield from cast("list[_R]", rows)

    def all(self) -> Generator[_R, None, None]:
        """Every row, lazily — ``where()`` with no criteria."""
        yield from self.where()
