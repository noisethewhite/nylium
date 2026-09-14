from __future__ import annotations

from typing import Any, TypeVar, cast

import sqlalchemy as sqla
from sqlalchemy import Engine, Executable, Select
from sqlalchemy.engine import Result, ScalarResult
from sqlalchemy.orm import Query, Session

from nylium.database.sessioncontext import SessionContext

_T = TypeVar("_T")


class _DatabaseMeta(type):
    @property
    def session(cls) -> Session:
        return SessionContext.get_session()

    @property
    def engine(cls) -> Engine:
        return SessionContext.get_engine()


class Database(metaclass=_DatabaseMeta):
    """Ambient handle on the current session.

    The statement proxies below are verbatim delegations — they exist so
    the tables layer writes ``Database.get(...)`` instead of reaching
    through ``Database.session``. Commit stays a unit-of-work concern of
    ``@databasemethod`` (the outermost call commits once, atomically);
    statements never commit individually.
    """

    @classmethod
    def get(cls, entity: type[_T], ident: object) -> _T | None:
        return cls.session.get(entity, ident)

    @classmethod
    def scalar(cls, statement: Select[tuple[_T]]) -> _T | None:
        return cls.session.scalar(statement)

    @classmethod
    def scalars(cls, statement: Select[tuple[_T]]) -> ScalarResult[_T]:
        return cls.session.scalars(statement)

    @classmethod
    def execute(cls, statement: Executable) -> Result[Any]:  # pyright: ignore[reportExplicitAny]
        return cls.session.execute(statement)

    @classmethod
    def add(cls, instance: object) -> None:
        cls.session.add(instance)

    @classmethod
    def delete(cls, instance: object) -> None:
        cls.session.delete(instance)

    @classmethod
    def flush(cls) -> None:
        cls.session.flush()

    @classmethod
    def merge(cls, instance: _T) -> _T:
        return cls.session.merge(instance)

    @classmethod
    def query(
        cls, *entities: Any  # pyright: ignore[reportAny, reportExplicitAny]
    ) -> Query[Any]:  # pyright: ignore[reportExplicitAny]
        return cls.session.query(*entities)  # pyright: ignore[reportAny]


def database_size_bytes() -> int:
    """Server-level footprint of the nylium database (ADR-0015 storage stats).

    An engine query, not a session/table read — lives beside ``Database`` so
    the api layer never reaches for SQLAlchemy directly.
    """
    with Database.engine.connect() as connection:
        return cast(
            int,
            connection.execute(
                sqla.select(sqla.func.pg_database_size(sqla.func.current_database()))
            ).scalar_one(),
        )
