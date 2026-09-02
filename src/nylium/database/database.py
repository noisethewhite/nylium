from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Concatenate, ParamSpec, TypeVar, Literal, cast, overload
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
    @overload
    def sessionmethod(*, bundled: Literal[False], commit: bool) -> Callable[[Callable[Concatenate[_C, Session, _P], _R]], Callable[Concatenate[_C, _P], _R]]: ...

    @staticmethod
    @overload
    def sessionmethod(*, bundled: Literal[True], commit: bool) -> Callable[[Callable[Concatenate[_C, _P], _R]], Callable[Concatenate[_C, _P], _R]]: ...

    @staticmethod
    def sessionmethod(*, bundled: bool, commit: bool) -> Callable[[Callable[Concatenate[_C, Session, _P], _R]], Callable[Concatenate[_C, _P], _R]] | Callable[[Callable[Concatenate[_C, _P], _R]], Callable[Concatenate[_C, _P], _R]]:
        def decorator(func: Callable[Concatenate[_C, Session, _P], _R] | Callable[Concatenate[_C, _P], _R]) -> Callable[Concatenate[_C, _P], _R]:
            def wrapper(cls: _C, *args: _P.args, **kwargs: _P.kwargs) -> _R:
                local_session = LocalSession(Database.engine)
                try:
                    if bundled:
                        value = cast(Callable[Concatenate[_C, _P], _R], func)(cls, *args, **kwargs)
                    else:
                        value = cast(Callable[Concatenate[_C, Session, _P], _R], func)(cls, local_session.value, *args, **kwargs)
                    if commit:
                        local_session.commit()
                    return value
                finally:
                    local_session.close()
            return wrapper
        return decorator
