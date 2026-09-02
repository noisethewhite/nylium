from __future__ import annotations

import threading
from collections.abc import Callable
from functools import wraps
from typing import Concatenate, ParamSpec, TypeVar

import sqlalchemy as sqla
from sqlalchemy.orm import Session

from nylium.system import Environment


_engine: sqla.Engine | None = None
_local = threading.local()


_C = TypeVar("_C")
_R = TypeVar("_R")
_P = ParamSpec("_P")


class Database:
    @staticmethod
    def engine() -> sqla.Engine:
        global _engine
        if _engine is None:
            _engine = sqla.create_engine(Environment.database_url, pool_pre_ping=True, echo=False)
        return _engine

    @staticmethod
    def _session_for_thread() -> tuple[Session, bool]:
        # One Session per thread; nested sessionmethod calls share it and
        # only the outermost call owns closing/committing.
        session = getattr(_local, "session", None)
        if session is not None:
            return session, False
        session = Session(Database.engine())
        _local.session = session
        return session, True

    @staticmethod
    def _close_session(session: Session) -> None:
        # close() rolls back any uncommitted transaction
        try:
            session.close()
        finally:
            _local.session = None

    @staticmethod
    def sessionmethod(func: Callable[Concatenate[_C, Session, _P], _R]) -> Callable[Concatenate[_C, _P], _R]:
        @wraps(func)
        def wrapper(cls: _C, *args: _P.args, **kwargs: _P.kwargs) -> _R:
            session, duty_to_close = Database._session_for_thread()
            try:
                return func(cls, session, *args, **kwargs)
            finally:
                if duty_to_close:
                    Database._close_session(session)

        return wrapper

    @staticmethod
    def sessionmethod_begin(func: Callable[Concatenate[_C, Session, _P], _R]) -> Callable[Concatenate[_C, _P], _R]:
        # Plain commit, not begin_nested: the outermost call commits once,
        # nested calls no-op, so a public call stays one atomic transaction.
        @wraps(func)
        def wrapper(cls: _C, *args: _P.args, **kwargs: _P.kwargs) -> _R:
            session, duty_to_close = Database._session_for_thread()
            try:
                value = func(cls, session, *args, **kwargs)
                if duty_to_close:
                    session.commit()
                return value
            finally:
                if duty_to_close:
                    Database._close_session(session)

        return wrapper
