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
    class sessionmethod:
        @staticmethod
        def no_commit(func: Callable[Concatenate[_C, Session, _P], _R]) -> Callable[Concatenate[_C, _P], _R]:
            @wraps(func)
            def wrapper(cls: _C, *args: _P.args, **kwargs: _P.kwargs) -> _R:
                local_session = LocalSession(Database.engine)
                try:
                    return func(cls, local_session.value, *args, **kwargs)
                finally:
                    local_session.close()
            return wrapper

        @staticmethod
        def bundled_no_commit(func: Callable[Concatenate[_C, _P], _R]) -> Callable[Concatenate[_C, _P], _R]:
            @wraps(func)
            def wrapper(cls: _C, *args: _P.args, **kwargs: _P.kwargs) -> _R:
                local_session = LocalSession(Database.engine)
                try:
                    return func(cls, *args, **kwargs)
                finally:
                    local_session.close()
            return wrapper

        @staticmethod
        def with_commit(func: Callable[Concatenate[_C, Session, _P], _R]) -> Callable[Concatenate[_C, _P], _R]:
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

        @staticmethod
        def bundled_with_commit(func: Callable[Concatenate[_C, _P], _R]) -> Callable[Concatenate[_C, _P], _R]:
            @wraps(func)
            def wrapper(cls: _C, *args: _P.args, **kwargs: _P.kwargs) -> _R:
                local_session = LocalSession(Database.engine)
                try:
                    value = func(cls, *args, **kwargs)
                    local_session.commit()
                    return value
                finally:
                    local_session.close()
            return wrapper
