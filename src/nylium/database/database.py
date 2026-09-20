from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

import sqlalchemy as sqla
from sqlalchemy import Engine, Executable, Select
from sqlalchemy.engine import Result, ScalarResult
from sqlalchemy.orm import Query, Session

from nylium.database.sessioncontext import SessionContext

_T = TypeVar("_T")
_P = ParamSpec("_P")
_R = TypeVar("_R")


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
    ``@Database.commit_after_this`` (the outermost call commits once,
    atomically); statements never commit individually.

    ``use_same_session`` and ``commit_after_this`` are classmethod
    decorators: apply them as ``@Database.use_same_session`` /
    ``@Database.commit_after_this``.
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

    @classmethod
    def use_same_session(cls, func: Callable[_P, _R]) -> Callable[_P, _R]:
        """Run ``func`` inside a SessionContext without committing.

        Joins the outermost session (or opens one that a nested
        ``commit_after_this`` will commit). Use for reads and for the inner
        steps of a multi-step write: the outermost call commits once,
        atomically.
        """

        @wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            with SessionContext():
                return func(*args, **kwargs)

        return wrapper

    @classmethod
    def commit_after_this(cls, func: Callable[_P, _R]) -> Callable[_P, _R]:
        """Run ``func`` inside a SessionContext and commit when it owns the session.

        The outermost call commits once, atomically; nested calls share the
        owner's session and leave the commit to it, so a failure mid-operation
        rolls back instead of leaving a half-written object.
        """

        @wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            with SessionContext() as ctx:
                value = func(*args, **kwargs)
                if ctx.owns_session:
                    SessionContext.get_session().commit()
                return value

        return wrapper


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
