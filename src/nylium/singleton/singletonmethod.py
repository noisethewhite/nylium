from __future__ import annotations
from typing import TypeVar, ParamSpec, Generic, Concatenate
import collections.abc as cabc
import functools
from .singletonregistry import SingletonRegistry


_T = TypeVar("_T")
_R = TypeVar("_R")
_P = ParamSpec("_P")


class singletonmethod(Generic[_T, _P, _R]):
    _func: cabc.Callable[Concatenate[_T, _P], _R]

    def __init__(self, func: cabc.Callable[Concatenate[_T, _P], _R]) -> None:
        self._func = func

    def __get__(self, _: _T | None, owner: type[_T]) -> cabc.Callable[_P, _R]:
        if owner not in SingletonRegistry.data.keys():
            raise TypeError("singletonproperty must only be used inside a singleton.")
        @functools.wraps(self._func)
        def method(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            instance = owner()
            return self._func(instance, *args, **kwargs)
        return method
