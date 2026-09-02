from __future__ import annotations
import sqlalchemy as sqla
from sqlalchemy.orm import Session
from collections.abc import Callable
from typing import TypeVar, ParamSpec, Concatenate
from nylium.system import Environment
from functools import wraps


_engine: sqla.Engine | None = None
_session: Session | None = None


_C = TypeVar("_C")
_R = TypeVar("_R")
_P = ParamSpec("_P")


class Database:
    @staticmethod
    def _get_engine() -> sqla.Engine:
        global _engine
        if _engine is None:
            _engine = sqla.create_engine(Environment.database_url, pool_pre_ping=True, echo=False)
        return _engine

    @staticmethod
    def sessionmethod(func: Callable[Concatenate[_C, Session, _P], _R]) -> Callable[Concatenate[_C, _P], _R]:
        def wrapper(cls: _C, *args: _P.args, **kwargs: _P.kwargs) -> _R:
            global _session
            duty_to_close = False
            if _session is None:
                _session = Session(Database._get_engine())
                duty_to_close = True
            value = func(cls, _session, *args, **kwargs)
            if duty_to_close:
                _session.close()
                _session = None
            return value
        return wrapper

    @staticmethod
    def _beginmethod(func: Callable[Concatenate[_C, Session, _P], _R]) -> Callable[Concatenate[_C, Session, _P], _R]:
        @wraps(func)
        def wrapper(cls: _C, session: Session, *args: _P.args, **kwargs: _P.kwargs) -> _R:
            with session.begin_nested():
                return func(cls, session, *args, **kwargs)
        return wrapper

    @staticmethod
    def sessionmethod_begin(func: Callable[Concatenate[_C, Session, _P], _R]) -> Callable[Concatenate[_C, _P], _R]:
        return Database.sessionmethod(Database._beginmethod(func))
