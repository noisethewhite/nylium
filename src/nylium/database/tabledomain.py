"""Writable domain objects over table rows (ADR-0011).

A domain object snapshots one row and exposes its columns as
``tableproperty`` fields: instance access reads the snapshot, instance
assignment writes through to the table in a ``@databasemethod``. The table's
abstraction is a ``Mapping[K, DomainObject]`` (built next to the row in
``nylium/tables/``), so callers read and write one representation instead of
row + store + view.

Only the generic base lives here. Concrete domain objects (``UnitPart`` etc.)
are defined next to their row type and point ``__table__`` at it, keeping
this module free of ``nylium.tables`` imports — importing a table's package
triggers ``tables/__init__``, which reaches back for the domain base (an
import cycle). ``Base`` is a ``TYPE_CHECKING``-only reference.

The descriptor protocol between ``tableproperty`` and ``TableDomain`` is
public on purpose (project lint forbids cross-class private access):
``__table__``, ``snapshot`` and ``persist`` are the seams the descriptor
drives, named in the SQLAlchemy framework-attribute style.

The primary key is generic: most tables key on ``uuid`` (the subclasses then
annotate ``uuid: UUID``), but auth tables key on ``token_hash`` /
``challenge``. The PK name is read off the mapped row at runtime, so one base
serves both. The PK is identity — set at creation, never written through.
"""
from __future__ import annotations

from collections.abc import Generator, Iterator, Mapping
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Generic,
    TypeVar,
    cast,
    overload,
    override,
)

import sqlalchemy as sqla

from nylium.database import Database
from nylium.database.databasemethod import databasemethod
from nylium.database.sessioncontext import SessionContext

if TYPE_CHECKING:
    from nylium.tables.base import Base

_T = TypeVar("_T")
_K = TypeVar("_K")
_D = TypeVar("_D", bound="TableDomain")


def _column(table: type[Base], name: str) -> sqla.Column[object]:
    """The row's column by name, typed — getattr alone comes back Any."""
    return cast(sqla.Column[object], getattr(table, name))


def _tableproperties(cls: type[TableDomain]) -> dict[str, tableproperty[object]]:
    """All tableproperty fields of a domain class, base classes first."""
    found: dict[str, tableproperty[object]] = {}
    for klass in reversed(cls.__mro__):
        members = cast("Mapping[str, object]", vars(klass))
        for name, candidate in members.items():
            if isinstance(candidate, tableproperty):
                found[name] = cast("tableproperty[object]", candidate)
    return found


class TableDomain:
    """Base for a writable domain object snapshotting one row (ADR-0011).

    The primary key is a ``tableproperty`` like any other column — it sits
    in ``snapshot`` and is read the same way. It is identity: set at
    creation, and by convention never reassigned (writing a PK would issue a
    nonsensical UPDATE). Subclasses set ``__table__`` to their row class and
    declare the PK's real type (``uuid: tableproperty[UUID]`` for most,
    ``token_hash: tableproperty[str]`` in auth). Every other ``tableproperty``
    column lives in ``snapshot`` and persists on assignment.
    """

    __table__: ClassVar[type[Base]]
    snapshot: dict[str, object]

    def __init__(self, snapshot: dict[str, object]) -> None:
        self.snapshot = snapshot

    @classmethod
    def _pk_name(cls) -> str:
        """The row's PK column name (``uuid`` for most, ``token_hash`` /
        ``challenge`` in auth). Read off the mapped row so one base serves
        both shapes."""
        return cast(str, sqla.inspect(cls.__table__).primary_key[0].name)

    @classmethod
    def from_row(cls, row: Base) -> TableDomain:
        """Snapshot one row into a domain object (public: tableproperty and
        the table Mappings build objects through here)."""
        snapshot = {
            name: cast(object, getattr(row, prop.column))
            for name, prop in _tableproperties(cls).items()
        }
        return cls(snapshot=snapshot)

    @classmethod
    def primary_key(cls) -> sqla.Column[object]:
        """The row's PK column, for the table Mappings' scans."""
        pk = sqla.inspect(cls.__table__).primary_key
        return cast(sqla.Column[object], pk[0])

    @databasemethod(commit=True)
    def persist(self, column: str, value: object) -> None:
        """Write one column through: UPDATE … SET column = value WHERE pk.

        ``commit=True`` joins the owner-commits-once semantics: nested writes
        inside an outer databasemethod share its session and commit once at
        the boundary, so a multi-field edit stays atomic.
        """
        pk_name = self._pk_name()
        pk = _column(self.__table__, pk_name)
        _ = Database.session.execute(
            sqla.update(self.__table__)
            .where(pk == self.snapshot[pk_name])
            .values({column: value})
        )


class tableproperty(Generic[_T]):
    """A domain field backed by one row column (ADR-0011).

    Instance access reads the object's snapshot; instance assignment writes
    the value into the snapshot and issues an ``UPDATE`` through the owner's
    ``persist``. Class access returns the descriptor itself so
    ``Xxx.field.list_for(value)`` can run a reverse lookup on the column.

    ``column``/``owner`` are bound by ``__set_name__`` at class-creation;
    the class-level defaults only satisfy the strict-initializer lint and
    are never observed.
    """

    column: str = ""
    owner: type[TableDomain] = TableDomain

    def __set_name__(self, owner: type[TableDomain], name: str) -> None:
        self.owner = owner
        self.column = name

    @overload
    def __get__(self, obj: None, objtype: None = None) -> tableproperty[_T]: ...

    @overload
    def __get__(self, obj: TableDomain, objtype: type | None = None) -> _T: ...

    def __get__(
        self, obj: TableDomain | None, objtype: type | None = None
    ) -> tableproperty[_T] | _T:
        if obj is None:
            return self
        return cast(_T, obj.snapshot[self.column])

    def __set__(self, obj: TableDomain, value: _T) -> None:
        obj.snapshot[self.column] = value
        obj.persist(self.column, value)

    def list_for(self, value: _T) -> Generator[TableDomain, None, None]:
        """Every domain object whose column equals ``value``, lazily.

        The rows are materialised inside one SessionContext (closed before the
        first yield) so a caller that abandons iteration early never strands a
        live connection. Yields the owner's concrete domain type
        (``UnitPart`` etc.) — the declared base keeps the descriptor generic
        over one TypeVar.
        """
        table = self.owner.__table__
        column = _column(table, self.column)
        with SessionContext():
            domains = [
                self.owner.from_row(row)
                for row in Database.session.scalars(
                    sqla.select(table).where(column == value)
                )
            ]
        yield from domains


class TableMapping(Generic[_K, _D], Mapping[_K, _D]):
    """The ``Mapping[K, Domain]`` shape of a table (ADR-0011).

    Subclasses set ``__domain__`` to their concrete domain type; the domain's
    ``__table__`` supplies the row class. ``get``/``__getitem__``/``__iter__``
    /``__len__`` come from here — the table-specific query helpers (``by_name``,
    ``list_for``, write ops) live on the concrete Mapping next to the row.
    ``_K`` is the PK type: ``UUID`` for domain tables, ``str``/``bytes`` for
    the auth session/challenge tables.
    """

    __domain__: ClassVar[type[TableDomain]]

    @databasemethod(commit=False)
    @override
    def __getitem__(self, key: _K) -> _D:
        row = Database.session.get(self.__domain__.__table__, key)
        if row is None:
            raise KeyError(key)
        return cast(_D, self.__domain__.from_row(row))

    @override
    def __iter__(self) -> Iterator[_K]:
        pk = self.__domain__.primary_key()
        with SessionContext():
            keys = list(Database.session.scalars(sqla.select(pk)))
        yield from cast("list[_K]", keys)

    @override
    def __len__(self) -> int:
        with SessionContext():
            return int(
                Database.session.scalar(
                    sqla.select(sqla.func.count()).select_from(
                        self.__domain__.__table__
                    )
                )
                or 0
            )
