from __future__ import annotations
from contextvars import ContextVar, Token
from typing import TypeVar, Generic, cast
import threading


_T = TypeVar("_T")
_local = threading.local()


class LocalCtxVar(Generic[_T]):
    _name: str
    _default: _T

    def __init__(self, name: str, default: _T) -> None:
        self._name = name
        self._default = default

    @property
    def name(self) -> str:
        return self._name

    @property
    def _ctxvar(self) -> ContextVar[_T]:
        if not hasattr(_local, self.name):
            setattr(_local, self.name, ContextVar[_T](self.name, default=self._default))
        return cast(ContextVar[_T], getattr(_local, self.name))

    def set(self, value: _T) -> Token[_T]:
        return self._ctxvar.set(value)

    def get(self) -> _T:
        return self._ctxvar.get()

    def reset(self, token: Token[_T]) -> None:
        self._ctxvar.reset(token)
