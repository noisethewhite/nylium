from __future__ import annotations

import threading
from collections.abc import Callable
from functools import wraps
from typing import Concatenate, ParamSpec, TypeVar
import sqlalchemy as sqla
from sqlalchemy.orm import Session

from nylium.system import Environment
from nylium.database.localsession import LocalSession


_engine: sqla.Engine | None = None
_local = threading.local()


_C = TypeVar("_C")
_R = TypeVar("_R")
_P = ParamSpec("_P")


class _DatabaseMeta(type):
    @property
    def engine(cls) -> sqla.Engine:
        global _engine
        if _engine is None:
            _engine = sqla.create_engine(Environment.database_url, pool_pre_ping=True, echo=False)
        return _engine


class Database(metaclass=_DatabaseMeta):
    @staticmethod
    def sessionmethod(func: Callable[Concatenate[_C, Session, _P], _R]) -> Callable[Concatenate[_C, _P], _R]:
        @wraps(func)
        def wrapper(cls: _C, *args: _P.args, **kwargs: _P.kwargs) -> _R:
            local_session = LocalSession(Database.engine)
            try:
                return func(cls, local_session.value, *args, **kwargs)
            finally:
                local_session.close()
        return wrapper

    @staticmethod
    def sessionmethod_begin(func: Callable[Concatenate[_C, Session, _P], _R]) -> Callable[Concatenate[_C, _P], _R]:
        # Plain commit, not begin_nested: the outermost call commits once,
        # nested calls no-op, so a public call stays one atomic transaction.
        @wraps(func)
        def wrapper(cls: _C, *args: _P.args, **kwargs: _P.kwargs) -> _R:
            local_session = LocalSession(Database.engine)
            try:
                value = func(cls, local_session.value, *args, **kwargs)
                local_session.commit()
                return value
            finally:
                local_session.close()
        return wrapper
