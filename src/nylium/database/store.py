"""Store: a Mapping-shaped access layer over the tables (ADR-0010).

A Store wraps one SQLAlchemy row type and exposes the native Mapping
contract — ``__getitem__`` / ``get`` / ``__contains__`` / ``__iter__`` /
``__len__`` — so callers read and iterate any table the same way instead
of through a per-class vocabulary of ``*_by_*`` / ``all_*`` helpers.

Only the generic base lives here. Concrete stores (``TypeStore`` etc.) are
defined next to their row type in ``nylium/tables/`` and inject the model
through ``__init__``. That keeps this module free of ``nylium.tables``
imports: importing a table's package triggers ``tables/__init__``, whose
props/instances modules reach back for a store — an import cycle. The
model is a ``TYPE_CHECKING``-only reference, so the runtime never touches
the tables package.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING, Generic, TypeVar, cast

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.databasemethod import databasemethod

if TYPE_CHECKING:
    from nylium.tables.base import Base

_K = TypeVar("_K")
_V = TypeVar("_V")


class Store(Mapping[_K, _V], Generic[_K, _V]):
    """Mapping contract over a single-column-primary-key table."""

    model: type[Base]

    def __init__(self, model: type[Base]) -> None:
        self.model = model

    def _pk(self) -> sqla.Column[object]:
        pk = sqla.inspect(self.model).primary_key
        if len(pk) != 1:
            raise ValueError(
                f"Store needs a single-column primary key; {self.model.__name__} has {len(pk)}"
            )
        return cast(sqla.Column[object], pk[0])

    @databasemethod(commit=False)
    def __getitem__(self, key: _K) -> _V:
        row = Database.session.get(self.model, key)
        if row is None:
            raise KeyError(key)
        return cast(_V, row)

    @databasemethod(commit=False)
    def __iter__(self) -> Iterator[_K]:
        keys = Database.session.scalars(sqla.select(self._pk())).all()
        return iter(cast("list[_K]", list(keys)))

    @databasemethod(commit=False)
    def __len__(self) -> int:
        count = Database.session.scalar(
            sqla.select(sqla.func.count()).select_from(self.model)
        )
        return int(count or 0)

    @databasemethod(commit=False)
    def all(self) -> list[_V]:
        """Every row in one query — avoids N+1 through the values() mixin."""
        rows = Database.session.scalars(sqla.select(self.model)).all()
        return cast("list[_V]", list(rows))
