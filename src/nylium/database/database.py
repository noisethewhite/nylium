from __future__ import annotations
import sqlalchemy as sqla
from typing import TypeVar, overload

from nylium.singleton import singleton, singletonmethod, singletonproperty
from nylium.system import Environment


_T = TypeVar(name="_T")


@singleton
class Database:
    _engine: sqla.Engine

    def __init__(self) -> None:
        self._engine = sqla.create_engine(Environment.database_url, pool_pre_ping=True, echo=False)

    @singletonproperty
    def engine(self) -> sqla.Engine:
        return self._engine

    @singletonmethod
    @overload
    def execute(self, _statement: sqla.Executable, _expected_type: None) -> None: ...

    @singletonmethod
    @overload
    def execute(self, _statement: sqla.Executable, _expected_type: type[_T]) -> _T: ...

    @singletonmethod
    def execute(self, _statement: sqla.Executable, _expected_type: type[_T] | None = None) -> _T | None:
        commit: bool = _expected_type is None
        with self._engine.connect() as conn:
            result: sqla.CursorResult[_T] = conn.execute(_statement)
            if commit:
                conn.commit()
            if _expected_type is not None:
                value: object | None = result.scalar_one_or_none()
                if value is not None and not isinstance(value, _expected_type):
                    raise RuntimeError(f"Expected {_expected_type}, got {type(value)}.")
                return value
            return None

